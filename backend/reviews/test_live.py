import json
import tempfile
from pathlib import Path
from unittest import mock

import joblib
import numpy as np
import pandas as pd
import requests
from django.test import TestCase
from rest_framework.test import APITestCase

from reviews.models import Comment, PullRequest
from reviews.services import save_analysis
from scoring import live
from scoring.ml_based import FEATURES, build_models, make_matrix


def fake_record(repo="octo/demo", number=42, merged=True):
    return {
        "repo": repo, "number": number, "title": "BUG: fix overflow in parser",
        "body": "Fixes the overflow.", "author": "dev",
        "created_at": "2026-11-01T10:00:00Z",
        "merged_at": "2026-11-02T10:00:00Z" if merged else None,
        "additions": 120, "deletions": 30, "changed_files": 2, "commits": 3,
        "comments": 0, "review_comments": 1,
        "files": [{"filename": "src/parser.c", "status": "modified", "additions": 100, "deletions": 20},
                  {"filename": "src/util.py", "status": "modified", "additions": 20, "deletions": 10}],
        "diff": "--- src/parser.c\n@@ -1 +1 @@\n-old\n+new\n--- src/util.py\n@@ -1 +1 @@\n-a\n+b",
    }


LLM_OK = {"score": 71, "label": "high", "summary": "Fixes an overflow.",
          "reasons": ["touches native parser code"], "input_tokens": 3000, "output_tokens": 400}


def train_tiny_model(model_dir, training_keys=()):
    """A real (tiny) fitted model + reference distribution, saved like train_final does."""
    rng = np.random.RandomState(0)
    df = pd.DataFrame({c: rng.randint(0, 5, 300) for c in FEATURES})
    y = (rng.rand(300) < 0.15).astype(int)
    model = build_models(y)["logistic_regression"].fit(make_matrix(df), y)
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / "logistic_regression.joblib")
    ref = sorted(model.predict_proba(make_matrix(df))[:, 1].tolist())
    (model_dir / "reference_probs.json").write_text(json.dumps(ref))
    (model_dir / "training_keys.json").write_text(json.dumps(list(training_keys)))


class ParseUrlTests(TestCase):
    def test_accepted_forms(self):
        for text in ["https://github.com/numpy/numpy/pull/123", "http://github.com/numpy/numpy/pull/123/files",
                     "  https://github.com/numpy/numpy/pull/123  ", "numpy/numpy#123",
                     "https://github.com/scikit-learn/scikit-learn/pull/9?diff=split"]:
            repo, number = live.parse_pr_url(text)
            self.assertEqual(number, 123 if "9?" not in text else 9)
            self.assertIn("/", repo)

    def test_rejected(self):
        for bad in ["", None, "hello", "https://github.com/numpy/numpy", "https://github.com/numpy/numpy/issues/5",
                    "https://example.com/a/b/pull/1x"]:
            with self.assertRaises(live.AnalysisError) as cm:
                live.parse_pr_url(bad)
            self.assertEqual(cm.exception.status, 400)


class FetchErrorTests(TestCase):
    def _http_error(self, code):
        resp = requests.Response(); resp.status_code = code
        return requests.HTTPError(response=resp)

    def test_404_403_and_network(self):
        with mock.patch.object(live, "fetch_record", side_effect=self._http_error(404)):
            with self.assertRaises(live.AnalysisError) as cm:
                live.fetch_pr("a/b", 1)
            self.assertEqual(cm.exception.status, 404)
        with mock.patch.object(live, "fetch_record", side_effect=self._http_error(403)):
            with self.assertRaises(live.AnalysisError) as cm:
                live.fetch_pr("a/b", 1)
            self.assertEqual(cm.exception.status, 502)
        with mock.patch.object(live, "fetch_record", side_effect=requests.ConnectionError("down")):
            with self.assertRaises(live.AnalysisError) as cm:
                live.fetch_pr("a/b", 1)
            self.assertEqual(cm.exception.status, 502)


class AnalyzeUrlTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.models = Path(self.tmp.name) / "models"
        self.cache = Path(self.tmp.name) / "cache"
        live._ml_cache.clear()
        self.patches = [
            mock.patch.object(live, "MODEL_DIR", self.models),
            mock.patch("scoring.llm_based.CACHE_DIR", self.cache),
            mock.patch.object(live, "fetch_pr", return_value=fake_record()),
            mock.patch.object(live, "make_client", return_value=object()),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])
        self.addCleanup(self.tmp.cleanup)

    URL = "https://github.com/octo/demo/pull/42"

    def test_all_three_scores(self):
        train_tiny_model(self.models)
        with mock.patch.object(live, "score_with_llm", return_value=dict(LLM_OK)) as llm:
            out = live.analyze_url(self.URL)
        self.assertEqual(set(out["scores"]), {"rule_based", "ml_based", "llm_based"})
        self.assertEqual(out["scores"]["llm_based"]["score"], 71)
        self.assertEqual(out["summary"], "Fixes an overflow.")
        self.assertEqual(out["warnings"], [])
        ml = out["scores"]["ml_based"]
        self.assertTrue(0 <= ml["score"] <= 100 and ml["label"] in {"low", "medium", "high"})
        llm.assert_called_once()

    def test_untrained_ml_model_is_a_warning_not_a_failure(self):
        with mock.patch.object(live, "score_with_llm", return_value=dict(LLM_OK)):
            out = live.analyze_url(self.URL)
        self.assertNotIn("ml_based", out["scores"])
        self.assertIn("rule_based", out["scores"])
        self.assertTrue(any("train_final" in w for w in out["warnings"]))

    def test_llm_failure_keeps_the_other_scores(self):
        train_tiny_model(self.models)
        with mock.patch.object(live, "score_with_llm", side_effect=RuntimeError("credit balance too low")):
            out = live.analyze_url(self.URL)
        self.assertEqual(set(out["scores"]), {"rule_based", "ml_based"})
        self.assertTrue(any("credit balance too low" in w for w in out["warnings"]))
        self.assertIn("No LLM summary", out["summary"])

    def test_pr_in_training_data_is_flagged(self):
        train_tiny_model(self.models, training_keys=["octo/demo#42"])
        with mock.patch.object(live, "score_with_llm", return_value=dict(LLM_OK)):
            out = live.analyze_url(self.URL)
        self.assertTrue(any("training data" in w for w in out["warnings"]))

    def test_llm_result_is_cached_and_force_bypasses_it(self):
        train_tiny_model(self.models)
        with mock.patch.object(live, "score_with_llm", return_value=dict(LLM_OK)) as llm:
            live.analyze_url(self.URL)
            live.analyze_url(self.URL)
            self.assertEqual(llm.call_count, 1)          # second call served from cache
            live.analyze_url(self.URL, force=True)
            self.assertEqual(llm.call_count, 2)


class SaveAnalysisTests(TestCase):
    def result(self, rec=None, llm=True):
        rec = rec or fake_record()
        scores = {"rule_based": {"score": 40, "label": "medium", "reasons": ["r"]},
                  "ml_based": {"score": 80, "label": "medium", "reasons": ["m"]}}
        if llm:
            scores["llm_based"] = {"score": 71, "label": "high", "reasons": ["l"]}
        return {"record": rec, "scores": scores, "summary": "A summary.", "warnings": []}

    def test_creates_a_live_pr(self):
        pr = save_analysis(self.result())
        self.assertEqual((pr.source, pr.status, pr.actual_outcome), ("live", "merged", None))
        self.assertEqual(pr.scores.count(), 3)
        self.assertEqual(pr.files_changed, ["src/parser.c", "src/util.py"])

    def test_open_pr_without_merge_date(self):
        pr = save_analysis(self.result(fake_record(merged=False)))
        self.assertEqual(pr.status, "unmerged")
        self.assertIsNotNone(pr.merged_at)               # falls back to created_at so it sorts sensibly

    def test_reanalysis_updates_in_place_and_keeps_comments(self):
        pr = save_analysis(self.result())
        Comment.objects.create(pull_request=pr, body="keep me")
        again = save_analysis(self.result(llm=False))
        self.assertEqual(again.pk, pr.pk)
        self.assertEqual(PullRequest.objects.count(), 1)
        self.assertEqual(Comment.objects.count(), 1)

    def test_dataset_pr_keeps_its_source_and_outcome(self):
        existing = PullRequest.objects.create(repo="octo/demo", number=42, title="old", source="dataset",
                                              actual_outcome=True)
        pr = save_analysis(self.result())
        self.assertEqual(pr.pk, existing.pk)
        self.assertEqual((pr.source, pr.actual_outcome), ("dataset", True))
        self.assertEqual(pr.title, "BUG: fix overflow in parser")


class AnalyzeEndpointTests(APITestCase):
    def test_success_returns_detail_with_warnings(self):
        result = {"record": fake_record(), "summary": "S.", "warnings": ["heads up"],
                  "scores": {"rule_based": {"score": 40, "label": "medium", "reasons": ["r"]}}}
        with mock.patch("reviews.views.analyze_url", return_value=result):
            res = self.client.post("/api/analyze/", {"url": "https://github.com/octo/demo/pull/42"}, format="json")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["source"], "live")
        self.assertEqual(data["warnings"], ["heads up"])
        self.assertEqual(set(data["scores"]), {"rule_based"})
        self.assertEqual(self.client.get(f"/api/prs/{data['id']}/").status_code, 200)

    def test_missing_url_is_400(self):
        self.assertEqual(self.client.post("/api/analyze/", {}, format="json").status_code, 400)

    def test_analysis_errors_become_clean_responses(self):
        for status in (400, 404, 502):
            with mock.patch("reviews.views.analyze_url", side_effect=live.AnalysisError("nope", status)):
                res = self.client.post("/api/analyze/", {"url": "x"}, format="json")
            self.assertEqual((res.status_code, res.json()["detail"]), (status, "nope"))