from django.test import TestCase
from rest_framework.test import APITestCase

from .models import Comment, EvaluationSnapshot, PullRequest, Score


def make_pr(number, title="BUG: fix x", repo="numpy/numpy", labels=None):
    pr = PullRequest.objects.create(
        repo=repo, number=number, title=title, diff="--- a.py\n+x = 1",
        files_changed=["a.py"], additions=1, deletions=0, summary="s", actual_outcome=False)
    for method, label in (labels or {}).items():
        Score.objects.create(pull_request=pr, method=method,
                             score={"low": 10, "medium": 45, "high": 80}[label],
                             label=label, reasons=["because"])
    return pr


class PullRequestApiTests(APITestCase):
    def setUp(self):
        self.a = make_pr(1, labels={"rule_based": "low", "ml_based": "high", "llm_based": "medium"})
        self.b = make_pr(2, title="ENH: add option", repo="pallets/flask", labels={"rule_based": "low"})
        self.c = make_pr(3)   # no scores yet

    def test_list_matches_frontend_contract(self):
        res = self.client.get("/api/prs/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 3)
        first = res.json()[0]
        self.assertEqual(set(first), {"id", "repo", "pr_number", "title", "status",
                                      "created_at", "overall_risk"})

    def test_overall_risk_is_highest_label(self):
        by_number = {p["pr_number"]: p for p in self.client.get("/api/prs/").json()}
        self.assertEqual(by_number[1]["overall_risk"], "high")
        self.assertEqual(by_number[2]["overall_risk"], "low")
        self.assertIsNone(by_number[3]["overall_risk"])

    def test_list_filters(self):
        self.assertEqual(len(self.client.get("/api/prs/?repo=pallets/flask").json()), 1)
        self.assertEqual(len(self.client.get("/api/prs/?search=option").json()), 1)

    def test_detail_has_scores_per_method(self):
        res = self.client.get(f"/api/prs/{self.a.id}/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(set(data["scores"]), {"rule_based", "ml_based", "llm_based"})
        self.assertEqual(set(data["scores"]["ml_based"]), {"score", "label", "reasons"})
        for key in ("diff", "files_changed", "summary", "actual_outcome", "pr_number"):
            self.assertIn(key, data)

    def test_detail_404(self):
        self.assertEqual(self.client.get("/api/prs/9999/").status_code, 404)


class CommentApiTests(APITestCase):
    def setUp(self):
        self.pr = make_pr(1)

    def test_post_then_list(self):
        res = self.client.post(f"/api/prs/{self.pr.id}/comments/",
                               {"body": "Looks risky", "line_ref": 12}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["user"], "guest")
        listed = self.client.get(f"/api/prs/{self.pr.id}/comments/").json()
        self.assertEqual([c["body"] for c in listed], ["Looks risky"])

    def test_comments_are_per_pr(self):
        other = make_pr(2)
        self.client.post(f"/api/prs/{self.pr.id}/comments/", {"body": "x"}, format="json")
        self.assertEqual(self.client.get(f"/api/prs/{other.id}/comments/").json(), [])

    def test_empty_comment_rejected(self):
        res = self.client.post(f"/api/prs/{self.pr.id}/comments/", {"body": ""}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_comment_on_missing_pr(self):
        res = self.client.post("/api/prs/9999/comments/", {"body": "x"}, format="json")
        self.assertEqual(res.status_code, 404)


class EvaluationApiTests(APITestCase):
    def test_summary_404_until_loaded_then_200(self):
        self.assertEqual(self.client.get("/api/evaluation/summary/").status_code, 404)
        EvaluationSnapshot.objects.create(data={"n_prs": 428, "methods": {}})
        res = self.client.get("/api/evaluation/summary/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["n_prs"], 428)

    def test_per_pr_rows(self):
        make_pr(1, labels={"rule_based": "low", "ml_based": "high"})
        row = self.client.get("/api/evaluation/prs/").json()[0]
        self.assertEqual(row["rule_based_score"], 10)
        self.assertEqual(row["ml_based_score"], 80)
        self.assertIsNone(row["llm_based_score"])
        self.assertIs(row["actual_outcome"], False)


class ImportKeepsCommentsTests(TestCase):
    def test_update_or_create_pattern_keeps_comments(self):
        """import_data uses update_or_create, so a re-import must not delete comments."""
        pr = make_pr(1)
        Comment.objects.create(pull_request=pr, body="keep me")
        PullRequest.objects.update_or_create(repo=pr.repo, number=pr.number,
                                             defaults={"title": "retitled"})
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(PullRequest.objects.get(pk=pr.pk).title, "retitled")