"""Feature extraction shared by the rule-based and ML scorers."""
import math
import re

SENSITIVE = re.compile(
    r"(auth|login|logout|password|passwd|payment|billing|checkout|invoice|secret|token|"
    r"permission|crypto|security|session|oauth|credential)", re.I)
CONFIG = re.compile(
    r"(dockerfile|docker-compose|\.github/workflows|\.env|settings|config|requirements.*\.txt|"
    r"package(-lock)?\.json|pyproject\.toml|poetry\.lock|yarn\.lock|\.ya?ml$|terraform)", re.I)
MIGRATION = re.compile(r"(migrations?/|alembic|\.sql$)", re.I)
TEST = re.compile(r"(^|/)(tests?|__tests__|spec)(/|_)|(_test|\.test|\.spec)\.\w+$|(^|/)test_", re.I)
DOC = re.compile(r"(\.md|\.rst|\.txt|\.adoc)$|(^|/)docs?/", re.I)

FEATURE_NAMES = [
    "lines_added", "lines_deleted", "log_churn", "files_changed", "max_file_churn",
    "sensitive_files", "config_files", "migration_files", "test_files", "source_files",
]


def _files(pr) -> list[dict]:
    if pr.files:
        return pr.files
    return [{"filename": "unknown", "additions": pr.additions, "deletions": pr.deletions}]


def extract(pr) -> dict:
    files = _files(pr)
    sensitive = config = migration = tests = docs = source = 0
    max_churn = 0
    for f in files:
        name = f.get("filename", "")
        churn = f.get("additions", 0) + f.get("deletions", 0)
        max_churn = max(max_churn, churn)
        if TEST.search(name):
            tests += 1
        elif DOC.search(name):
            docs += 1
        else:
            source += 1
        if SENSITIVE.search(name):
            sensitive += 1
        if MIGRATION.search(name):
            migration += 1
        elif CONFIG.search(name):
            config += 1
    added, deleted = pr.additions, pr.deletions
    return {
        "lines_added": added,
        "lines_deleted": deleted,
        "log_churn": math.log1p(added + deleted),
        "files_changed": max(pr.changed_files, len(files)),
        "max_file_churn": max_churn,
        "sensitive_files": sensitive,
        "config_files": config,
        "migration_files": migration,
        "test_files": tests,
        "source_files": source,
        "doc_files": docs,  # used by the rules only, not an ML feature
    }
