from celery import shared_task

from scoring.pipeline import analyze_pull_request

from . import github_client
from .models import PullRequest
from .services import get_repo, upsert_pull_request


@shared_task
def ingest_pr_task(full_name: str, number: int) -> int:
    """Fetch a PR from GitHub, store it, then queue scoring."""
    data = github_client.fetch_pr(full_name, number)
    pr = upsert_pull_request(get_repo(full_name), data)
    analyze_pr_task.delay(pr.id)
    return pr.id


@shared_task
def analyze_pr_task(pr_id: int, methods: list | None = None) -> int:
    pr = PullRequest.objects.get(pk=pr_id)
    analyze_pull_request(pr, methods)
    return pr.id
