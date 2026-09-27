"""Batch mode data collection: pull merged PRs from a public repo and label reverted ones.

Label rules (deliberately simple and explainable in a viva):
  * A PR is 'reverted' if a later revert PR points at it ("Reverts owner/repo#123" or Revert "<title>").
  * Revert PRs themselves are kept but left 'unknown' (not evaluated).
  * Other merged PRs older than --clean-after-days are 'clean' (weak label: no revert *detected*).
  * Newer PRs stay 'unknown' - they haven't had time to fail yet.
Extend with bug-linked / hotfixed labels later (e.g. SZZ-style linking) in label_outcomes().
"""
import re
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core import github_client
from core.models import PullRequest
from core.services import get_repo, upsert_pull_request

REVERTS_REF = re.compile(r"Reverts?\s+[\w.-]+/[\w.-]+#(\d+)", re.I)
REVERT_TITLE = re.compile(r'^Revert\s+"(.+)"', re.I)


def label_outcomes(repo, clean_after_days: int) -> dict:
    prs = list(PullRequest.objects.filter(repo=repo, is_historical=True))
    by_number = {p.number: p for p in prs}
    by_title = {p.title: p for p in prs}
    reverted, revert_prs = set(), set()
    for p in prs:
        m1, m2 = REVERTS_REF.search(p.body or ""), REVERT_TITLE.match(p.title)
        if m1 or m2:
            revert_prs.add(p.id)
            target = by_number.get(int(m1.group(1))) if m1 else by_title.get(m2.group(1))
            if target:
                reverted.add(target.id)
    cutoff = timezone.now() - timedelta(days=clean_after_days)
    counts = {"reverted": 0, "clean": 0, "unknown": 0}
    for p in prs:
        if p.id in reverted:
            outcome = "reverted"
        elif p.id in revert_prs or not p.merged_at or p.merged_at > cutoff:
            outcome = "unknown"
        else:
            outcome = "clean"
        PullRequest.objects.filter(pk=p.pk).update(outcome=outcome)
        counts[outcome] += 1
    return counts


class Command(BaseCommand):
    help = "Collect merged PRs from a public repo and auto-label outcomes."

    def add_arguments(self, parser):
        parser.add_argument("repo", help="owner/name, e.g. django/django")
        parser.add_argument("--limit", type=int, default=200)
        parser.add_argument("--clean-after-days", type=int, default=30)

    def handle(self, *args, repo, limit, clean_after_days, **opts):
        repo_obj = get_repo(repo)
        n = 0
        for data in github_client.iter_merged_prs(repo, limit):
            upsert_pull_request(repo_obj, data, is_historical=True)
            n += 1
            if n % 10 == 0:
                self.stdout.write(f"  collected {n}/{limit}")
        counts = label_outcomes(repo_obj, clean_after_days)
        self.stdout.write(self.style.SUCCESS(f"Collected {n} PRs from {repo}. Labels: {counts}"))
