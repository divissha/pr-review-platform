import json
import tempfile
from pathlib import Path
from unittest import mock

import joblib
from django.test import SimpleTestCase

from scoring import live

LLM = {"score": 40, "label": "low", "reasons": ["r"], "summary": "s"}
REC = {"changed_files": 1, "additions": 1, "deletions": 0, "files": []}


class MlFailureTests(SimpleTestCase):
    def setUp(self):
        live._ml_cache.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for target, value in [
            ("MODEL_DIR", Path(self.tmp.name)),
            ("fetch_pr", mock.Mock(return_value=REC)),
            ("pr_features", mock.Mock(return_value={})),
            ("score_pr", mock.Mock(return_value={"score": 10, "label": "low", "reasons": []})),
            ("load_cached", mock.Mock(return_value=LLM)),
            ("fetch_head", mock.Mock(return_value=("o/r", "abc"))),
            ("analyze_static", mock.Mock(return_value=None)),
        ]:
            p = mock.patch.object(live, target, value)
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(live._ml_cache.clear)

    def _save_model(self, sklearn_version):
        d = Path(self.tmp.name)
        joblib.dump({"dummy": 1}, d / "logistic_regression.joblib")
        (d / "reference_probs.json").write_text(json.dumps([0.1, 0.2]))
        (d / "model_meta.json").write_text(json.dumps({"sklearn": sklearn_version}))

    def test_a_crashing_model_becomes_a_warning(self):
        with mock.patch.object(live, "ml_score", side_effect=AttributeError("multi_class")):
            out = live.analyze_url("o/r#1")
        self.assertEqual(set(out["scores"]), {"rule_based", "llm_based"})
        text = " ".join(out["warnings"])
        self.assertIn("ML scoring failed", text)
        self.assertIn("train_final", text)

    def test_scikit_learn_version_mismatch_is_explained(self):
        self._save_model("0.0.1")
        out = live.analyze_url("o/r#1")
        self.assertNotIn("ml_based", out["scores"])
        self.assertIn("trained with scikit-learn 0.0.1", " ".join(out["warnings"]))

    def test_matching_version_passes_the_check(self):
        import sklearn
        self._save_model(sklearn.__version__)
        bundle = live._load_ml()
        self.assertIsNotNone(bundle)