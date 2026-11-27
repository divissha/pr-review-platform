"""
Static analysis of the files a pull request changes, using Bandit (a security
linter for Python).

This is shown next to the risk scores as extra evidence. It does NOT feed into
any score, so the evaluation results stay untouched.

Bandit needs whole files, not diffs, so the changed Python files are fetched
from GitHub at the PR's head commit. Each finding is then marked as sitting on
a line this PR added, or elsewhere in the same file.
"""
import base64
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

from scoring.llm_based import split_diff_blocks

MAX_FILES = 15
MAX_FILE_BYTES = 200_000
MAX_FINDINGS = 100
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def added_line_numbers(patch):
    """Line numbers (in the NEW version of the file) of the lines a unified-diff
    patch adds."""
    added, new_line = set(), None
    for line in patch.splitlines():
        m = HUNK_RE.match(line)
        if m:
            new_line = int(m.group(1))
            continue
        if new_line is None or line.startswith("\\"):   # before the first hunk / "\ No newline"
            continue
        if line.startswith("+"):
            added.add(new_line)
            new_line += 1
        elif line.startswith("-"):
            continue                                     # removed lines don't exist in the new file
        else:
            new_line += 1                                # context line
    return added


def python_files(record):
    """Changed, non-test Python files that still exist after the PR."""
    names = [f["filename"] for f in record["files"]
             if f["filename"].lower().endswith(".py")
             and "test" not in f["filename"].lower()
             and f.get("status") != "removed"]
    return names[:MAX_FILES]


def _fetch_text(get, repo, path, sha):
    data = get(f"/repos/{repo}/contents/{quote(path)}", {"ref": sha}).json()
    if isinstance(data, dict) and data.get("encoding") == "base64":
        raw = base64.b64decode(data["content"])
        if len(raw) <= MAX_FILE_BYTES:
            return raw.decode("utf-8", errors="replace")
    return None


def run_bandit(files):
    """files: {repo_relative_path: source}. Returns Bandit's raw results, each with
    a 'path' key holding the repo-relative path."""
    if importlib.util.find_spec("bandit") is None:
        raise RuntimeError("Bandit is not installed. Run: pip install bandit")
    with tempfile.TemporaryDirectory() as tmp:
        for rel, text in files.items():
            dest = Path(tmp) / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", tmp, "-f", "json", "-q"],
            capture_output=True, text=True, timeout=60)   # exit code 1 just means "found issues"
    out = proc.stdout[proc.stdout.find("{"):] if "{" in proc.stdout else ""
    if not out.strip():
        raise RuntimeError(f"Bandit produced no output: {proc.stderr.strip()[:200]}")
    results = json.loads(out).get("results", [])
    paths = sorted(files, key=len, reverse=True)          # longest first: 'src/a.py' before 'a.py'
    for r in results:
        name = r["filename"].replace("\\", "/")
        r["path"] = next((p for p in paths if name.endswith("/" + p)), name)
    return results


def analyze_static(record, head_repo, sha, get):
    """Returns {tool, files_scanned, findings, note}. `get(url, params)` is the
    GitHub GET helper (injected so this is easy to test)."""
    result = {"tool": "bandit", "files_scanned": 0, "findings": [], "note": None}
    candidates = python_files(record)
    if not candidates:
        result["note"] = "No Python source files changed (Bandit analyses Python only)."
        return result
    if not sha:
        raise RuntimeError("Could not determine the PR's head commit.")

    texts, skipped = {}, 0
    for path in candidates:
        try:
            text = _fetch_text(get, head_repo, path, sha)
        except Exception:  # noqa: BLE001 - one unreadable file must not stop the rest
            text = None
        if text is None:
            skipped += 1
        else:
            texts[path] = text
    if not texts:
        result["note"] = "Could not fetch the changed Python files from GitHub."
        return result

    added = {name: added_line_numbers(block) for name, block in split_diff_blocks(record)}
    findings = []
    for r in run_bandit(texts):
        lines = set(r.get("line_range") or [r["line_number"]])
        findings.append({
            "rule_id": r["test_id"], "rule": r["test_name"],
            "severity": r["issue_severity"].lower(), "confidence": r["issue_confidence"].lower(),
            "file": r["path"], "line": r["line_number"], "message": r["issue_text"],
            "on_changed_line": bool(lines & added.get(r["path"], set())),
        })
    findings.sort(key=lambda f: (not f["on_changed_line"],
                                 SEVERITY_ORDER.get(f["severity"], 3), f["file"], f["line"]))
    result.update(files_scanned=len(texts), findings=findings[:MAX_FINDINGS])
    if skipped:
        result["note"] = f"{skipped} file(s) could not be fetched and were skipped."
    return result