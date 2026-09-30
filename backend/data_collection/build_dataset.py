"""
Step 2: turn the raw PR downloads into a labeled dataset.

Usage (run from the backend/ folder):
    python data_collection/build_dataset.py

Reads:  backend/data/raw/*.jsonl
Writes: backend/data/dataset.csv

Labels (proxy signals for "this PR turned out to be risky"):
  label_reverted : a later PR reverted this one
  label_hotfix   : a later "fix" PR touched the same source files within HOTFIX_DAYS
  label_bug_ref  : a later "fix" PR mentioned this PR's number within BUGREF_DAYS
  risky          : any of the above
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
OUT_PATH = DATA_DIR / "dataset.csv"

HOTFIX_DAYS = 14
BUGREF_DAYS = 30
WINDOW = timedelta(days=max(HOTFIX_DAYS, BUGREF_DAYS))

CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".rs",
            ".c", ".cc", ".cpp", ".h", ".cs", ".php", ".kt", ".swift"}
REVERT_BODY_RE = re.compile(r"Reverts\s+[\w.\-]+/[\w.\-]+#(\d+)", re.I)
REVERT_TITLE_RE = re.compile(r'^Revert\s+"(.+)"', re.I)
FIX_RE = re.compile(r"\b(fix|fixes|fixed|hotfix|regression|bug)\b", re.I)

NON_RISK_PREFIX_RE = re.compile(r"^(doc|docs|ci|mnt|maint|tst|test|style|typo|typ)\s*[:\-]", re.I)


TITLE_WORD_RE = re.compile(r"[a-z]{4,}")


def titles_too_similar(a, b):
    """True if two PR titles share most of their meaningful words —
    a sign of a backport/duplicate rather than an independent fix."""
    wa, wb = set(TITLE_WORD_RE.findall(a.lower())), set(TITLE_WORD_RE.findall(b.lower()))
    if not wa or not wb:
        return False
    return len(wa & wb) / len(wa | wb) >= 0.6


def parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def is_source_file(path):
    p = path.lower()
    return "test" not in p and Path(p).suffix in CODE_EXT


def load_repo(path):
    prs = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            p = json.loads(line)
            p["merged_dt"] = parse_dt(p["merged_at"])
            p["src_files"] = {
                f["filename"] for f in p["files"]
                if is_source_file(f["filename"]) and (f["additions"] + f["deletions"]) >= 3
            }
            p["is_revert_pr"] = p["title"].lower().startswith("revert")
            prs.append(p)
    prs.sort(key=lambda p: p["merged_dt"])
    return prs


def label_repo(prs):
    # 1) which PRs got reverted?
    by_title = {p["title"]: p["number"] for p in prs}
    reverted = set()
    for p in prs:
        if not p["is_revert_pr"]:
            continue
        m = REVERT_BODY_RE.search(p["body"] or "")
        if m:
            reverted.add(int(m.group(1)))
        else:
            t = REVERT_TITLE_RE.match(p["title"])
            if t and t.group(1) in by_title:
                reverted.add(by_title[t.group(1)])

    # 2) hotfix / bug-reference labels from later "fix" PRs
    newest = prs[-1]["merged_dt"]
    for i, p in enumerate(prs):
        p["label_reverted"] = p["number"] in reverted
        p["label_hotfix"] = False
        p["label_bug_ref"] = False
        p["hotfix_pr"] = None
        p["bugref_pr"] = None
        ref = re.compile(rf"#{p['number']}\b")
        is_functional = not NON_RISK_PREFIX_RE.match(p["title"])
        for q in prs[i + 1:] if is_functional else []:
            gap = q["merged_dt"] - p["merged_dt"]
            if gap > WINDOW:
                break
            if q["is_revert_pr"] or not FIX_RE.search(q["title"]):
                continue
            if (
                gap <= timedelta(days=10)
                and p["src_files"]
                and len(p["src_files"] & q["src_files"]) / len(p["src_files"]) >= 0.5
                and len(q["src_files"]) <= 4
                and f"#{p['number']}" not in q["title"]
                and not titles_too_similar(p["title"], q["title"])
            ):
                p["label_hotfix"] = True
                p["hotfix_pr"] = p["hotfix_pr"] or q["number"]
            if (
                gap <= timedelta(days=BUGREF_DAYS)
                and ref.search(f"{q['title']} {q['body']}")
                and not re.search(rf"\(#{p['number']}\)\s*$", q["title"])
                and not titles_too_similar(p["title"], q["title"])
            ):
                p["label_bug_ref"] = True
                p["bugref_pr"] = p["bugref_pr"] or q["number"]
        # PRs merged too recently haven't had time to be reverted or fixed yet
        p["label_window_complete"] = p["merged_dt"] <= newest - WINDOW
        p["risky"] = p["label_reverted"] or p["label_hotfix"] or p["label_bug_ref"]
    return prs


def to_row(p):
    return {
        "repo": p["repo"],
        "number": p["number"],
        "title": p["title"],
        "author": p["author"],
        "merged_at": p["merged_at"],
        "additions": p["additions"],
        "deletions": p["deletions"],
        "changed_files": p["changed_files"],
        "commits": p["commits"],
        "comments": p["comments"],
        "review_comments": p["review_comments"],
        "n_source_files": len(p["src_files"]),
        "touches_tests": any("test" in f["filename"].lower() for f in p["files"]),
        "is_revert_pr": p["is_revert_pr"],
        "label_reverted": p["label_reverted"],
        "label_hotfix": p["label_hotfix"],
        "label_bug_ref": p["label_bug_ref"],
        "hotfix_pr": p["hotfix_pr"],
        "bugref_pr": p["bugref_pr"],
        "risky": p["risky"],
        "label_window_complete": p["label_window_complete"],
    }


def main():
    rows = []
    for path in sorted(RAW_DIR.glob("*.jsonl")):
        prs = label_repo(load_repo(path))
        span = (prs[-1]["merged_dt"] - prs[0]["merged_dt"]).days
        print(f"{path.stem}: {len(prs)} PRs spanning {span} days")
        rows.extend(to_row(p) for p in prs)

    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False)

    # Only PRs with a full follow-up window, excluding the reverts themselves
    usable = df[df["label_window_complete"] & ~df["is_revert_pr"]]
    print(f"\nSaved {len(df)} rows -> {OUT_PATH}")
    print(f"Usable for evaluation: {len(usable)} PRs")
    for col in ["label_reverted", "label_hotfix", "label_bug_ref", "risky"]:
        print(f"  {col:15s}: {int(usable[col].sum()):4d}  ({usable[col].mean():.1%})")
    print("\nPer repo (usable PRs / risky):")
    print(usable.groupby("repo")["risky"].agg(["count", "sum"]).to_string())


if __name__ == "__main__":
    main()