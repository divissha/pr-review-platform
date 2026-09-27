"""Batch mode: run the scorers over historical PRs."""
from django.core.management.base import BaseCommand

from core.models import PullRequest
from scoring.pipeline import SCORERS, analyze_pull_request


class Command(BaseCommand):
    help = "Score historical PRs with the chosen methods."

    def add_arguments(self, parser):
        parser.add_argument("--methods", default="rule,ml", help="comma list of: rule,ml,llm")
        parser.add_argument("--limit", type=int, default=0, help="0 = all")
        parser.add_argument("--repo", default=None)
        parser.add_argument("--only-missing", action="store_true", help="skip PRs already scored by these methods")

    def handle(self, *args, methods, limit, repo, only_missing, **opts):
        methods = [m for m in methods.split(",") if m in SCORERS]
        qs = PullRequest.objects.filter(is_historical=True).order_by("id")
        if repo:
            qs = qs.filter(repo__full_name=repo)
        total = 0
        for pr in qs.iterator():
            if limit and total >= limit:
                break
            todo = methods
            if only_missing:
                done = set(pr.analyses.filter(status="ok").values_list("method", flat=True))
                todo = [m for m in methods if m not in done]
                if not todo:
                    continue
            analyze_pull_request(pr, todo)
            total += 1
            if total % 25 == 0:
                self.stdout.write(f"  scored {total} PRs...")
        self.stdout.write(self.style.SUCCESS(f"Scored {total} PRs with {methods}."))
