"""
Method 3: LLM-based risk scorer (prompt only, no fine-tuning).

The model reads PR metadata plus a truncated diff and returns a risk score
with reasons. Responses are cached on disk (one file per PR), so re-runs are
free and an interrupted run resumes where it stopped.

Fairness notes
  - The PR number, author and dates are NOT shown to the model.
  - Freeze the prompt BEFORE the full run. Editing it after looking at results
    on the evaluation PRs would be tuning on ~30 positives.
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from scoring.features import CODE_EXT, DATA_DIR

load_dotenv()

DEFAULT_MODEL = "claude-haiku-5-5"
CACHE_DIR = DATA_DIR / "llm_cache"
MAX_DIFF_CHARS = 12_000
MAX_BODY_CHARS = 1_500
MAX_FILES_LISTED = 40

SYSTEM_PROMPT = """You are an experienced software engineer reviewing a pull request that has just been merged into an open-source project. Estimate how likely it is that this change later causes a problem: a revert, a follow-up bug-fix pull request, or a reported regression.

Consider, for example:
- logic changes in core code paths, error handling, edge cases and boundary conditions
- memory management, reference counting, concurrency or other low-level hazards
- behaviour or API changes that could break existing users
- changes that look large, tangled or hard to review
- missing or weak test coverage for the behaviour that changed
Documentation, typo, formatting and purely mechanical changes are low risk.

Most merged pull requests never cause problems. Use the full 0-100 range, and reserve scores above 60 for changes where you can point to concrete reasons.

Respond with ONLY a JSON object and no other text:
{"risk_score": <integer 0-100>, "summary": "<one or two sentences on what the change does>", "risk_factors": ["<short concrete reason>", ...]}"""


# ---------------------------------------------------------------- prompt ----
def split_diff_blocks(pr):
    """Split the stored diff back into per-file blocks. Uses the known file
    names as markers, because a removed line such as '-- comment' also shows
    up as '--- comment' and would fool a naive split on '--- '."""
    diff, pos, starts = pr.get("diff", ""), 0, []
    for f in pr.get("files", []):
        marker = f"--- {f['filename']}\n"
        idx = diff.find(marker, pos)
        if idx == -1:
            continue
        starts.append((f["filename"], idx))
        pos = idx + len(marker)
    blocks = []
    for i, (name, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(diff)
        blocks.append((name, diff[start:end]))
    return blocks


def diff_excerpt(pr, budget=MAX_DIFF_CHARS):
    """Fit the diff into a character budget: source files first, then tests,
    then everything else, with a per-file cap so one huge file can't hide
    the rest."""
    blocks = split_diff_blocks(pr)
    if not blocks:
        return "(diff not available)"

    def priority(block):
        name = block[0].lower()
        if "test" in name:
            return 1                      # tests second
        return 0 if Path(name).suffix in CODE_EXT else 2   # source first, rest last

    blocks = sorted(blocks, key=priority)
    per_file = max(800, budget // min(len(blocks), 10))
    parts, used = [], 0
    for name, text in blocks:
        if used >= budget:
            parts.append(f"[... {len(blocks) - len(parts)} more file(s) omitted]")
            break
        chunk = text[: min(per_file, budget - used)]
        if len(chunk) < len(text):
            chunk += f"\n[... truncated {len(text) - len(chunk)} chars]"
        parts.append(chunk)
        used += len(chunk)
    return "\n".join(parts)


def build_user_prompt(pr):
    files = pr.get("files", [])
    listed = [f"{f['filename']} (+{f['additions']}/-{f['deletions']})"
              for f in files[:MAX_FILES_LISTED]]
    more = (f"\n... and {len(files) - MAX_FILES_LISTED} more files"
            if len(files) > MAX_FILES_LISTED else "")
    body = (pr.get("body") or "").strip()[:MAX_BODY_CHARS] or "(none)"
    return (
        f"Repository: {pr['repo']}\n"
        f"Title: {pr['title']}\n\n"
        f"Description:\n{body}\n\n"
        f"Files changed ({len(files)} total, +{pr['additions']}/-{pr['deletions']} lines):\n"
        + "\n".join(listed) + more + "\n\n"
        f"Diff (may be truncated):\n{diff_excerpt(pr)}"
    )


# -------------------------------------------------------------- response ----
def label_for(score):
    """Same thresholds as the rule-based scorer."""
    return "high" if score >= 60 else "medium" if score >= 30 else "low"


def parse_response(text):
    """Extract {score, label, summary, reasons} from the model's reply.
    Raises ValueError if the reply can't be used."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in reply")
    data = json.loads(text[start:end + 1])
    score = int(round(float(data["risk_score"])))
    if not 0 <= score <= 100:
        raise ValueError(f"score out of range: {score}")
    factors = data.get("risk_factors") or []
    if not isinstance(factors, list):
        factors = [str(factors)]
    return {
        "score": score,
        "label": label_for(score),
        "summary": str(data.get("summary", "")),
        "reasons": [str(x) for x in factors],
    }


# ------------------------------------------------------------------- API ----
def make_client():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to backend/.env")
    import anthropic  # imported here so --dry-run works without the package
    return anthropic.Anthropic(api_key=key, max_retries=5, timeout=90.0)


def score_with_llm(client, model, pr):
    resp = client.messages.create(
        model=model,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(pr)}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    result = parse_response(text)
    result["input_tokens"] = resp.usage.input_tokens
    result["output_tokens"] = resp.usage.output_tokens
    return result


# ----------------------------------------------------------------- cache ----
def _cache_path(model, pr):
    name = f"{pr['repo'].replace('/', '__')}__{pr['number']}.json"
    return CACHE_DIR / model / name


def load_cached(model, pr):
    path = _cache_path(model, pr)
    return json.loads(path.read_text()) if path.exists() else None


def save_cached(model, pr, result):
    path = _cache_path(model, pr)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result))