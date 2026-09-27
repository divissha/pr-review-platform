from .models import PullRequest, Repository


def get_repo(full_name: str, **extra) -> Repository:
    repo, _ = Repository.objects.get_or_create(full_name=full_name, defaults=extra)
    return repo


def upsert_pull_request(repo: Repository, data: dict, **extra) -> PullRequest:
    data = dict(data)
    number = data.pop("number")
    pr, _ = PullRequest.objects.update_or_create(repo=repo, number=number, defaults={**data, **extra})
    return pr
