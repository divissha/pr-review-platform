import time

from .base import ScorerUnavailable, label_for
from .llm_based import LLMScorer
from .ml_based import MLScorer
from .models import Analysis
from .rule_based import RuleBasedScorer

SCORERS = {"rule": RuleBasedScorer, "ml": MLScorer, "llm": LLMScorer}


def analyze_pull_request(pr, methods=None) -> list[Analysis]:
    """Run the requested scorers (default: all three). One failing scorer never blocks the others."""
    results = []
    for method in methods or SCORERS:
        if method not in SCORERS:
            continue
        started = time.perf_counter()
        empty = dict(risk=None, label="", summary="", reasons=[], model_version="", error="")
        try:
            r = SCORERS[method]().score(pr)
            fields = dict(empty, risk=r.risk, label=label_for(r.risk), summary=r.summary,
                          reasons=r.reasons, model_version=r.model_version, status="ok")
        except ScorerUnavailable as e:
            fields = dict(empty, status="unavailable", error=str(e))
        except Exception as e:  # noqa: BLE001 - store and move on
            fields = dict(empty, status="error", error=f"{type(e).__name__}: {e}")
        fields["latency_ms"] = int((time.perf_counter() - started) * 1000)
        obj, _ = Analysis.objects.update_or_create(pr=pr, method=method, defaults=fields)
        results.append(obj)
    return results
