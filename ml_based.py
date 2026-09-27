"""Method 2: a small trained model (logistic regression) over the shared features."""
from pathlib import Path

import joblib

from .base import BaseScorer, ScorerUnavailable, ScoreResult
from .features import FEATURE_NAMES, extract

ARTIFACT = Path(__file__).parent / "artifacts" / "ml_model.joblib"
_cache: dict = {"mtime": None, "bundle": None}


def load_bundle():
    if not ARTIFACT.exists():
        raise ScorerUnavailable("ML model not trained yet. Run: python manage.py train_ml")
    mtime = ARTIFACT.stat().st_mtime
    if _cache["mtime"] != mtime:
        _cache["bundle"], _cache["mtime"] = joblib.load(ARTIFACT), mtime
    return _cache["bundle"]


def holdout_ids() -> set | None:
    """PR ids the model never trained on. Evaluation should compare all methods on these."""
    try:
        return set(load_bundle().get("test_ids", []))
    except ScorerUnavailable:
        return None


class MLScorer(BaseScorer):
    method = "ml"

    def score(self, pr) -> ScoreResult:
        bundle = load_bundle()
        pipe, names = bundle["model"], bundle["features"]
        feats = extract(pr)
        x = [[feats[n] for n in names]]
        risk = float(pipe.predict_proba(x)[0][1])

        # Explain: coefficient * standardized value = push on the log-odds
        scaled = pipe.named_steps["scale"].transform(x)[0]
        coefs = pipe.named_steps["clf"].coef_[0]
        contrib = sorted(zip(names, coefs * scaled), key=lambda t: -abs(t[1]))[:3]
        reasons = [
            f"{n.replace('_', ' ')} pushes risk {'up' if c > 0 else 'down'} ({c:+.2f})" for n, c in contrib
        ]
        return ScoreResult(
            risk=risk,
            summary=f"Model estimates a {risk:.0%} chance this PR is later reverted or needs a fix.",
            reasons=reasons,
            model_version=bundle["version"],
        )
