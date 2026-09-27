"""The one interface all three scorers implement. Live mode and batch mode both call this."""
from dataclasses import dataclass, field

LOW_MAX = 0.35
HIGH_MIN = 0.65


class ScorerUnavailable(Exception):
    """Scorer can't run right now (no API key, model not trained...). Not a bug."""


@dataclass
class ScoreResult:
    risk: float                      # 0..1
    summary: str = ""
    reasons: list = field(default_factory=list)
    model_version: str = ""


def label_for(risk: float) -> str:
    if risk < LOW_MAX:
        return "low"
    if risk >= HIGH_MIN:
        return "high"
    return "medium"


class BaseScorer:
    method = ""

    def score(self, pr) -> ScoreResult:  # pr is a core.PullRequest
        raise NotImplementedError
