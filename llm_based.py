"""Method 3: send the diff to an LLM; get a plain-English summary plus a risk judgement."""
import json
import re

from django.conf import settings

from .base import BaseScorer, ScorerUnavailable, ScoreResult

SYSTEM = (
    "You are a senior engineer reviewing pull requests. Explain the change in plain English and "
    "estimate the probability that it later causes a bug, revert, or hotfix. Judge only from the "
    "information given. Be calibrated: most PRs are low risk. Respond with ONLY a JSON object: "
    '{"summary": "2-3 plain-English sentences", "risk": <number 0..1>, '
    '"reasons": ["up to 4 short reasons"]}'
)


def build_prompt(pr) -> str:
    limit = settings.LLM_MAX_DIFF_CHARS
    diff = pr.diff or "\n".join(f"{f['filename']}: +{f['additions']}/-{f['deletions']}" for f in pr.files)
    note = "\n[diff truncated]" if len(diff) > limit else ""
    return (
        f"Title: {pr.title}\n"
        f"Description: {(pr.body or '(none)')[:1500]}\n"
        f"Stats: {pr.changed_files} files, +{pr.additions}/-{pr.deletions}\n\n"
        f"Diff:\n{diff[:limit]}{note}"
    )


def parse_response(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError(f"LLM did not return JSON: {text[:200]}")
    data = json.loads(match.group(0))
    data["risk"] = max(0.0, min(1.0, float(data["risk"])))
    return data


class LLMScorer(BaseScorer):
    method = "llm"

    def score(self, pr) -> ScoreResult:
        if not settings.ANTHROPIC_API_KEY:
            raise ScorerUnavailable("Set ANTHROPIC_API_KEY to enable the LLM scorer.")
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=600,
            system=SYSTEM,
            messages=[{"role": "user", "content": build_prompt(pr)}],
        )
        data = parse_response(resp.content[0].text)
        return ScoreResult(
            risk=data["risk"],
            summary=data.get("summary", ""),
            reasons=data.get("reasons", [])[:4],
            model_version=settings.ANTHROPIC_MODEL,
        )
