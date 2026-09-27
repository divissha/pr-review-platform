import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from core.models import PullRequest, Repository
from scoring.evaluation import evaluate
from scoring.llm_based import parse_response
from scoring.models import Analysis
from scoring.pipeline import analyze_pull_request
from scoring.rule_based import RuleBasedScorer


def make_pr(number=1, files=None, outcome="unknown", **kw):
    repo, _ = Repository.objects.get_or_create(full_name="t/t")
    files = files or [{"filename": "app/utils.py", "additions": 10, "deletions": 2, "patch": "+x"}]
    return PullRequest.objects.create(
        repo=repo, number=number, title="t", files=files, outcome=outcome,
        additions=sum(f["additions"] for f in files), deletions=sum(f["deletions"] for f in files),
        changed_files=len(files), **kw)


class RuleScorerTests(TestCase):
    def test_docs_only_is_low(self):
        pr = make_pr(files=[{"filename": "README.md", "additions": 5, "deletions": 1}])
        self.assertLess(RuleBasedScorer().score(pr).risk, 0.1)

    def test_sensitive_large_untested_is_high(self):
        pr = make_pr(files=[{"filename": "app/auth/login.py", "additions": 600, "deletions": 50},
                            {"filename": "app/migrations/0001_x.py", "additions": 20, "deletions": 0}])
        r = RuleBasedScorer().score(pr)
        self.assertGreater(r.risk, 0.65)
        self.assertTrue(any("sensitive" in x.lower() for x in r.reasons))


class PipelineTests(TestCase):
    @override_settings(ANTHROPIC_API_KEY="")
    def test_unavailable_scorers_do_not_break_rule(self):
        pr = make_pr()
        analyze_pull_request(pr)
        by = {a.method: a for a in Analysis.objects.filter(pr=pr)}
        self.assertEqual(by["rule"].status, "ok")
        self.assertEqual(by["llm"].status, "unavailable")

    def test_reanalysis_is_idempotent(self):
        pr = make_pr()
        analyze_pull_request(pr, ["rule"])
        analyze_pull_request(pr, ["rule"])
        self.assertEqual(Analysis.objects.filter(pr=pr, method="rule").count(), 1)

    def test_llm_json_parsing(self):
        d = parse_response('Sure!\n{"summary": "s", "risk": 1.7, "reasons": ["a"]}')
        self.assertEqual(d["risk"], 1.0)


class EvaluationTests(TestCase):
    def test_metrics(self):
        for i, (outcome, rk) in enumerate([("reverted", 0.9), ("clean", 0.1), ("clean", 0.8), ("reverted", 0.2)]):
            pr = make_pr(number=i + 1, outcome=outcome)
            Analysis.objects.create(pr=pr, method="rule", risk=rk, status="ok")
        m = next(x for x in evaluate(0.5, holdout_only=False)["methods"] if x["method"] == "rule")
        self.assertEqual((m["tp"], m["fp"], m["fn"], m["tn"]), (1, 1, 1, 1))
        self.assertEqual(m["roc_auc"], 0.75)


class WebhookAndApiTests(TestCase):
    def _post(self, payload, secret="s3cret", event="pull_request", sign=True):
        body = json.dumps(payload).encode()
        sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers = {"HTTP_X_GITHUB_EVENT": event}
        if sign:
            headers["HTTP_X_HUB_SIGNATURE_256"] = sig
        return self.client.post("/api/webhooks/github/", body, content_type="application/json", **headers)

    @override_settings(GITHUB_WEBHOOK_SECRET="s3cret")
    def test_bad_signature_rejected(self):
        self.assertEqual(self._post({}, sign=False).status_code, 403)

    @override_settings(GITHUB_WEBHOOK_SECRET="s3cret")
    def test_opened_pr_is_queued(self):
        payload = {"action": "opened", "repository": {"full_name": "a/b"}, "pull_request": {"number": 7}}
        with patch("core.webhooks.ingest_pr_task.delay") as delay:
            resp = self._post(payload)
        self.assertEqual(resp.status_code, 202)
        delay.assert_called_once_with("a/b", 7)

    def test_comment_and_list_endpoints(self):
        pr = make_pr()
        analyze_pull_request(pr, ["rule"])
        self.assertEqual(self.client.get("/api/prs/").json()["count"], 1)
        r = self.client.post(f"/api/prs/{pr.id}/comments/", {"author": "kav", "body": "lgtm"},
                             content_type="application/json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(self.client.get(f"/api/prs/{pr.id}/").json()["comments"]), 1)


class LabelOutcomeTests(TestCase):
    def test_revert_detection(self):
        from datetime import timedelta

        from django.utils import timezone

        from core.management.commands.collect_prs import label_outcomes

        old = timezone.now() - timedelta(days=90)
        a = make_pr(number=1, is_historical=True, merged_at=old)
        b = make_pr(number=2, is_historical=True, merged_at=old)
        r = make_pr(number=3, is_historical=True, merged_at=old, body="Reverts t/t#1")
        r.title = "Revert something"; r.save()
        fresh = make_pr(number=4, is_historical=True, merged_at=timezone.now())
        label_outcomes(a.repo, 30)
        for p in (a, b, r, fresh):
            p.refresh_from_db()
        self.assertEqual((a.outcome, b.outcome, r.outcome, fresh.outcome), ("reverted", "clean", "unknown", "unknown"))
