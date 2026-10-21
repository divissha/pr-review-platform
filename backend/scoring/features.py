"""
Feature extraction shared by every scorer.

The same functions are used for batch evaluation (now) and for live PRs
inside the Django API (later), so a PR always gets identical features.
All features are knowable at merge time (nothing from after the merge).
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
DATASET_PATH = DATA_DIR / "dataset.csv"

# Keep these in sync with data_collection/build_dataset.py
CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".rs",
            ".c", ".cc", ".cpp", ".h", ".cs", ".php", ".kt", ".swift"}
NATIVE_EXT = {".c", ".cc", ".cpp", ".h", ".hpp", ".pyx", ".pxd", ".rs", ".cu"}
CONFIG_EXT = {".yml", ".yaml", ".toml", ".ini", ".cfg"}
DEPENDENCY_NAMES = {"setup.py", "pyproject.toml", "setup.cfg", "package.json",
                    "package-lock.json", "pipfile", "poetry.lock",
                    "environment.yml", "tox.ini"}
SENSITIVE_RE = re.compile(
    r"(auth|login|passw(or)?d|secret|token|crypto|security|permission|"
    r"session|payment|billing|oauth|credential)", re.I)


def _is_test(path):
    return "test" in path.lower()


def pr_features(pr):
    """Compute the feature dict for one PR record (same shape as the raw
    .jsonl records: additions, deletions, changed_files, commits,
    review_comments, files=[{filename, additions, deletions}, ...])."""
    files = pr.get("files", [])
    names = [f["filename"] for f in files]
    non_test = [n for n in names if not _is_test(n)]

    source_files = [
        f for f in files
        if not _is_test(f["filename"])
        and Path(f["filename"].lower()).suffix in CODE_EXT
        and (f["additions"] + f["deletions"]) >= 3
    ]
    n_source = len(source_files)
    touches_tests = any(_is_test(n) for n in names)
    additions, deletions = pr["additions"], pr["deletions"]

    return {
        "additions": additions,
        "deletions": deletions,
        "churn": additions + deletions,
        "changed_files": pr["changed_files"],
        "commits": pr["commits"],
        "review_comments": pr["review_comments"],
        "n_source_files": n_source,
        "touches_tests": int(touches_tests),
        "src_no_tests": int(n_source > 0 and not touches_tests),
        "sensitive_files": sum(1 for n in non_test if SENSITIVE_RE.search(n)),
        "native_files": sum(1 for n in non_test
                            if Path(n.lower()).suffix in NATIVE_EXT),
        "config_change": int(any(Path(n.lower()).suffix in CONFIG_EXT
                                 for n in non_test)),
        "dependency_change": int(any(
            Path(n.lower()).name in DEPENDENCY_NAMES
            or Path(n.lower()).name.startswith("requirements")
            for n in names)),
    }


def load_labeled_dataset():
    """Join dataset.csv labels with features computed from the raw PR files.
    Only usable PRs are returned (full 30-day window, not revert PRs)."""
    labels = pd.read_csv(DATASET_PATH)
    usable = labels[labels["label_window_complete"] & ~labels["is_revert_pr"]]

    raw = {}
    for path in RAW_DIR.glob("*.jsonl"):
        with open(path) as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    rec.pop("diff", None)  # not needed here; saves memory
                    raw[(rec["repo"], int(rec["number"]))] = rec

    rows = []
    for _, lab in usable.iterrows():
        rec = raw.get((lab["repo"], int(lab["number"])))
        if rec is None:
            continue
        row = pr_features(rec)
        row.update(repo=lab["repo"], number=int(lab["number"]),
                   title=lab["title"], risky=int(lab["risky"]))
        rows.append(row)
    return pd.DataFrame(rows)