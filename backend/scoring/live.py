"""
Live analysis of a single pull request, given its GitHub URL.

Fetches the PR from GitHub, then scores it with the rule-based scorer, the
saved ML model and the LLM. Used by the Django endpoint POST /api/analyze/.
"""
import json
import re
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import requests

from scoring.features import DATA_DIR, pr_features
from scoring.llm_based import (DEFAULT_MODEL, load_cached, make_client,
                               save_cached, score_with_llm)
from scoring.ml_based import make_matrix
from scoring.rule_based import score_pr

# data_collection/ holds plain scripts, so make its folder importable
_DC = Path(__file__).resolve().parent.parent / "data_collection"
if str(_DC) not in sys.path:
    sys.path.insert(0, str(_DC))
from collect_prs import fetch_record  # noqa: E402

MODEL_DIR = DATA_DIR / "models"
PR_URL_RE = re.compile(r"github\.com/([\w.\-]+)/([\w.\-]+)/pull/(\d+)", re.I)
SHORT_RE = re.compile(r"^([\w.\-]+)/([\w.\-]+)#(\d+)$")


class AnalysisError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def parse_pr_url(text):
    """'https://github.com/owner/repo/pull/123' or 'owner/repo#123' -> ('owner/repo', 123)"""
    text = (text or "").strip()
    m = PR_URL_RE.search(text) or SHORT_RE.match(text)
    if not m:
        raise AnalysisError("That doesn't look like a GitHub pull request URL, "
                            "e.g. https://github.com/owner/repo/pull/123")
    return f"{m.group(1)}/{m.group(2)}", int(m.group(3))


def fetch_pr(repo, number):
    try:
        return fetch_record(repo, {"number": number})
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else 0
        if code == 404:
            raise AnalysisError(f"{repo}#{number} was not found on GitHub "
                                f"(wrong number, or a private repository).", 404)
        raise AnalysisError(f"GitHub refused the request (HTTP {code}). "
                            f"Check GITHUB_TOKEN and your rate limit.", 502)
    except (requests.RequestException, RuntimeError) as e:
        raise AnalysisError(f"Could not reach GitHub: {e}", 502)


def percentile_label(pct):
    return "high" if pct >= 90 else "medium" if pct >= 70 else "low"


_ml_cache = {}


def _load_ml():
    """Returns (model, reference_probs) or None if the model hasn't been trained."""
    if "bundle" not in _ml_cache:
        model_path = MODEL_DIR / "logistic_regression.joblib"
        ref_path = MODEL_DIR / "reference_probs.json"
        if not (model_path.exists() and ref_path.exists()):
            return None          # not cached, so training later takes effect without a restart
        _ml_cache["bundle"] = (joblib.load(model_path),
                               np.array(json.loads(ref_path.read_text())))
    return _ml_cache["bundle"]


def ml_score(features):
    bundle = _load_ml()
    if bundle is None:
        return None
    model, ref = bundle
    prob = float(model.predict_proba(make_matrix(pd.DataFrame([features])))[0, 1])
    pct = float((ref <= prob).mean() * 100)
    top = max(1, round(100 - pct))
    return {"score": int(round(pct)), "label": percentile_label(pct),
            "reasons": [f"ranked in the top {top}% of PRs by the logistic-regression risk model"]}


def _in_training(repo, number):
    path = MODEL_DIR / "training_keys.json"
    return path.exists() and f"{repo}#{number}" in set(json.loads(path.read_text()))


def analyze_url(url, llm_model=DEFAULT_MODEL, force=False):
    """Returns {record, scores, summary, warnings}. A failing LLM or a missing ML
    model never blocks the analysis: the other scores are still returned."""
    repo, number = parse_pr_url(url)
    rec = fetch_pr(repo, number)
    features = pr_features(rec)

    scores, warnings, summary = {"rule_based": score_pr(features)}, [], ""

    ml = ml_score(features)
    if ml is None:
        warnings.append("ML model not trained yet. Run: python -m scoring.train_final")
    else:
        scores["ml_based"] = ml
        if _in_training(repo, number):
            warnings.append("This PR was part of the model's training data, "
                            "so its ML score is optimistic.")

    try:
        llm = None if force else load_cached(llm_model, rec)
        if llm is None:
            llm = score_with_llm(make_client(), llm_model, rec)
            save_cached(llm_model, rec, llm)
        scores["llm_based"] = {"score": llm["score"], "label": llm["label"],
                               "reasons": llm["reasons"]}
        summary = llm["summary"]
    except Exception as e:  # noqa: BLE001 - deliberately broad: degrade, don't fail
        warnings.append(f"LLM scoring failed: {e}")

    if not summary:
        summary = (f"{rec['changed_files']} files changed "
                   f"(+{rec['additions']}/-{rec['deletions']}). No LLM summary available.")
    return {"record": rec, "scores": scores, "summary": summary, "warnings": warnings}