import base64
import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase
from rest_framework.test import APITestCase

from reviews.services import save_analysis
from reviews.test_live import LLM_OK, fake_record, train_tiny_model
from scoring import live, static_analysis as sa

# The file as it exists at the PR's head commit. Line 4 is added by the PR; line 10 was already there.
HEAD_FILE = (
    "import subprocess\n"            # 1
    "\n"                             # 2
    "def run(cmd):\n"                # 3
    "    subprocess.call(cmd, shell=True)\n"   # 4  <- added by the PR (Bandit B602)
    "\n"                             # 5
    "\n"                             # 6
    "def other():\n"                 # 7
    "    return 1\n"                 # 8
    "\n"                             # 9
    "password = 'hunter2'\n"         # 10 <- pre-existing (Bandit B105)
)
PATCH = "@@ -3,3 +3,4 @@\n def run(cmd):\n+    subprocess.call(cmd, shell=True)\n \n \n"


def record_with(files, diff_blocks):
    rec = fake_record()
    rec["files"] = [{"filename": n, "status": st, "additions": 5, "deletions": 1} for n, st in files]
    rec["diff"] = "\n".join(f"--- {n}\n{p}" for n, p in diff_blocks)
    return rec


def fake_get(contents, calls=None):
    """Stand-in for the GitHub GET helper: serves file contents from a dict."""
    def get(url, params=None):
        path = url.split("/contents/", 1)[1]
        if calls is not None:
            calls.append(path)
        if path not in contents:
            raise RuntimeError("404")
        body = base64.b64encode(contents[path].encode()).decode()
        return mock.Mock(json=lambda: {"encoding": "base64", "content": body})
    return get


class AddedLineTests(TestCase):
    def test_single_hunk(self):
        self.assertEqual(sa.added_line_numbers("@@ -1,3 +1,4 @@\n a\n-b\n+c\n+d\n e"), {2, 3})

    def test_multiple_hunks(self):
        patch = "@@ -1,2 +1,3 @@\n a\n+x\n b\n@@ -10,2 +11,3 @@\n k\n+y\n m"
        self.assertEqual(sa.added_line_numbers(patch), {2, 12})

    def test_removed_line_that_looks_like_a_file_header_is_not_counted(self):
        # a removed SQL-style comment "-- note" shows up in a diff as "--- note"
        self.assertEqual(sa.added_line_numbers("@@ -1,2 +1,2 @@\n--- note\n+new\n keep"), {1})

    def test_no_newline_marker_does_not_shift_numbering(self):
        patch = "@@ -1,2 +1,3 @@\n a\n+b\n\\ No newline at end of file\n+c"
        self.assertEqual(sa.added_line_numbers(patch), {2, 3})

    def test_no_hunks(self):
        self.assertEqual(sa.added_line_numbers("just text"), set())


class RunBanditTests(TestCase):
    def test_real_bandit_finds_real_problems(self):
        results = sa.run_bandit({"pkg/app.py": HEAD_FILE})
        ids = {r["test_id"] for r in results}
        self.assertIn("B602", ids)        # subprocess call with shell=True
        self.assertIn("B105", ids)        # hard-coded password string
        self.assertTrue(all(r["path"] == "pkg/app.py" for r in results))

    def test_same_file_name_in_two_folders_maps_to_the_right_path(self):
        results = sa.run_bandit({"a.py": "password = 'x1'\n", "src/a.py": "eval('1+1')\n"})
        by_path = {r["path"]: r["test_id"] for r in results}
        self.assertEqual(by_path["a.py"], "B105")
        self.assertEqual(by_path["src/a.py"], "B307")

    def test_clean_code_has_no_findings(self):
        self.assertEqual(sa.run_bandit({"ok.py": "def f(x):\n    return x + 1\n"}), [])

    def test_missing_bandit_gives_a_clear_error(self):
        with mock.patch.object(sa.importlib.util, "find_spec", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "pip install bandit"):
                sa.run_bandit({"a.py": "x = 1\n"})


class AnalyzeStaticTests(TestCase):
    def rec(self):
        return record_with(
            [("src/app.py", "modified"), ("src/tests/test_app.py", "added"),
             ("docs/readme.md", "modified"), ("src/old.py", "removed")],
            [("src/app.py", PATCH)])

    def test_findings_are_split_into_changed_and_pre_existing(self):
        calls = []
        out = sa.analyze_static(self.rec(), "octo/demo", "abc123", fake_get({"src/app.py": HEAD_FILE}, calls))
        self.assertEqual(calls, ["src/app.py"])                  # tests, docs and removed files never fetched
        self.assertEqual(out["files_scanned"], 1)
        changed = [f for f in out["findings"] if f["on_changed_line"]]
        other = [f for f in out["findings"] if not f["on_changed_line"]]
        self.assertTrue(any(f["rule_id"] == "B602" and f["line"] == 4 for f in changed))
        self.assertTrue(any(f["rule_id"] == "B105" and f["line"] == 10 for f in other))
        self.assertTrue(out["findings"][0]["on_changed_line"])    # changed-line findings come first

    def test_non_python_pr_is_a_note_not_an_error(self):
        rec = record_with([("README.md", "modified"), ("src/x.c", "modified")], [])
        calls = []
        out = sa.analyze_static(rec, "octo/demo", "abc123", fake_get({}, calls))
        self.assertEqual((out["files_scanned"], out["findings"], calls), (0, [], []))
        self.assertIn("Python only", out["note"])

    def test_unfetchable_files_are_skipped_and_reported(self):
        rec = record_with([("src/app.py", "modified"), ("src/gone.py", "modified")], [("src/app.py", PATCH)])
        out = sa.analyze_static(rec, "octo/demo", "abc123", fake_get({"src/app.py": HEAD_FILE}))
        self.assertEqual(out["files_scanned"], 1)
        self.assertIn("1 file(s) could not be fetched", out["note"])

    def test_nothing_fetchable(self):
        rec = record_with([("src/app.py", "modified")], [("src/app.py", PATCH)])
        out = sa.analyze_static(rec, "octo/demo", "abc123", fake_get({}))
        self.assertEqual((out["files_scanned"], out["findings"]), (0, []))
        self.assertIn("Could not fetch", out["note"])

    def test_missing_head_commit_is_an_error(self):
        with self.assertRaisesRegex(RuntimeError, "head commit"):
            sa.analyze_static(self.rec(), "octo/demo", None, fake_get({}))


class LiveStaticIntegrationTests(TestCase):
    URL = "https://github.com/octo/demo/pull/42"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        models = Path(self.tmp.name) / "models"
        train_tiny_model(models)
        live._ml_cache.clear()
        patches = [
            mock.patch.object(live, "MODEL_DIR", models),
            mock.patch("scoring.llm_based.CACHE_DIR", Path(self.tmp.name) / "cache"),
            mock.patch.object(live, "fetch_pr", return_value=fake_record()),
            mock.patch.object(live, "make_client", return_value=object()),
            mock.patch.object(live, "score_with_llm", return_value=dict(LLM_OK)),
            mock.patch.object(live, "fetch_head", return_value=("octo/demo", "abc123")),
        ]
        for p in patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in patches])
        self.addCleanup(self.tmp.cleanup)

    def test_static_result_is_returned_and_saved(self):
        static = {"tool": "bandit", "files_scanned": 1, "note": None,
                  "findings": [{"rule_id": "B602", "on_changed_line": True}]}
        with mock.patch.object(live, "analyze_static", return_value=static):
            out = live.analyze_url(self.URL)
        self.assertEqual(out["static_analysis"], static)
        pr = save_analysis(out)
        pr.refresh_from_db()
        self.assertEqual(pr.static_analysis["findings"][0]["rule_id"], "B602")

    def test_static_failure_never_breaks_the_scores(self):
        with mock.patch.object(live, "analyze_static", side_effect=RuntimeError("Bandit is not installed")):
            out = live.analyze_url(self.URL)
        self.assertIsNone(out["static_analysis"])
        self.assertEqual(set(out["scores"]), {"rule_based", "ml_based", "llm_based"})
        self.assertTrue(any("Static analysis failed: Bandit is not installed" in w for w in out["warnings"]))


class StaticEndpointTests(APITestCase):
    def test_endpoint_and_detail_expose_static_analysis(self):
        static = {"tool": "bandit", "files_scanned": 1, "findings": [], "note": None}
        result = {"record": fake_record(), "summary": "S.", "warnings": [], "static_analysis": static,
                  "scores": {"rule_based": {"score": 40, "label": "medium", "reasons": ["r"]}}}
        with mock.patch("reviews.views.analyze_url", return_value=result):
            data = self.client.post("/api/analyze/", {"url": "https://github.com/octo/demo/pull/42"}, format="json").json()
        self.assertEqual(data["static_analysis"], static)
        self.assertEqual(self.client.get(f"/api/prs/{data['id']}/").json()["static_analysis"], static)