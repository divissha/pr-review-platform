"""
Method 1: transparent rule-based risk scorer.

IMPORTANT: every weight below was set a priori from general code-review
reasoning. None of them were tuned on the labeled dataset, so this scorer
is a fair, untrained baseline for the comparison.
"""


def score_pr(f):
    """f: feature dict from features.pr_features. Returns the same shape the
    frontend/API contract expects: {score, label, reasons}."""
    points = 0
    reasons = []

    def add(pts, reason):
        nonlocal points
        points += pts
        reasons.append(reason)

    churn = f["churn"]
    if churn >= 500:
        add(25, f"very large change ({churn} lines)")
    elif churn >= 200:
        add(15, f"large change ({churn} lines)")
    elif churn >= 50:
        add(8, f"moderate change ({churn} lines)")

    n = f["n_source_files"]
    if n >= 8:
        add(20, f"touches many source files ({n})")
    elif n >= 4:
        add(12, f"touches several source files ({n})")
    elif n >= 2:
        add(5, f"touches {n} source files")

    if f["src_no_tests"]:
        add(15, "source code changed without any test changes")
    if f["sensitive_files"] > 0:
        add(15, "touches security-sensitive code paths")
    if f["native_files"] > 0:
        add(10, "touches native (C/C++/Rust) code")
    if f["dependency_change"]:
        add(8, "changes dependency or build configuration")
    elif f["config_change"]:
        add(5, "changes configuration files")

    score = min(100, points)
    label = "high" if score >= 60 else "medium" if score >= 30 else "low"
    return {
        "score": score,
        "label": label,
        "reasons": reasons or ["no risk indicators triggered"],
    }