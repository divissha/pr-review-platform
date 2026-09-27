"""Score every method against real outcomes. This is the project's research result."""
from core.models import PullRequest

from .ml_based import holdout_ids
from .models import Analysis

METHODS = ["rule", "ml", "llm"]


def _safe_div(a, b):
    return a / b if b else 0.0


def evaluate(threshold: float = 0.5, repo: str | None = None, holdout_only: bool = True) -> dict:
    prs = PullRequest.objects.exclude(outcome=PullRequest.Outcome.UNKNOWN)
    if repo:
        prs = prs.filter(repo__full_name=repo)
    ids = set(prs.values_list("id", flat=True))
    held = holdout_ids() if holdout_only else None
    if held:
        ids &= held
    truth = {p.id: p.is_risky for p in prs.filter(id__in=ids)}

    out = {"threshold": threshold, "holdout_only": bool(held), "n_prs": len(truth),
           "n_risky": sum(truth.values()), "methods": []}

    for method in METHODS:
        rows = Analysis.objects.filter(pr_id__in=ids, method=method, status="ok", risk__isnull=False)
        y = [truth[a.pr_id] for a in rows]
        s = [a.risk for a in rows]
        pred = [v >= threshold for v in s]
        tp = sum(1 for t, p in zip(y, pred) if t and p)
        fp = sum(1 for t, p in zip(y, pred) if not t and p)
        fn = sum(1 for t, p in zip(y, pred) if t and not p)
        tn = sum(1 for t, p in zip(y, pred) if not t and not p)
        precision, recall = _safe_div(tp, tp + fp), _safe_div(tp, tp + fn)
        m = {
            "method": method, "n": len(y), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(precision, 3), "recall": round(recall, 3),
            "f1": round(_safe_div(2 * precision * recall, precision + recall), 3),
            "accuracy": round(_safe_div(tp + tn, len(y)), 3),
            "roc_auc": None, "pr_auc": None,
        }
        if len(set(y)) == 2:
            from sklearn.metrics import average_precision_score, roc_auc_score

            m["roc_auc"] = round(float(roc_auc_score(y, s)), 3)
            m["pr_auc"] = round(float(average_precision_score(y, s)), 3)
        out["methods"].append(m)
    return out
