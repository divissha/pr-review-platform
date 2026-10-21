"""Metrics shared by all three scorers, so they are compared identically."""
import numpy as np
from sklearn.metrics import (average_precision_score, f1_score,
                             precision_score, recall_score, roc_auc_score)


def evaluate(y_true, score, threshold=None, top_frac=0.10):
    """Threshold-free metrics (ROC-AUC, PR-AUC, precision/recall when the
    reviewer inspects only the riskiest top_frac of PRs), plus optional
    precision/recall/F1 at a fixed threshold."""
    y = np.asarray(y_true).astype(int)
    s = np.asarray(score, dtype=float)

    # Break ties randomly (fixed seed): many rule-based scores are identical,
    # and "first in file order" must not decide who lands in the top 10%.
    rng = np.random.RandomState(0)
    jittered = s + rng.uniform(0, 1e-9, size=len(s))

    k = max(1, int(round(top_frac * len(y))))
    top = np.argsort(-jittered)[:k]

    out = {
        "roc_auc": roc_auc_score(y, s),
        "pr_auc": average_precision_score(y, s),
        "precision_top10": y[top].mean(),
        "recall_top10": y[top].sum() / max(1, y.sum()),
    }
    if threshold is not None:
        pred = (s >= threshold).astype(int)
        out["precision"] = precision_score(y, pred, zero_division=0)
        out["recall"] = recall_score(y, pred, zero_division=0)
        out["f1"] = f1_score(y, pred, zero_division=0)
    return out