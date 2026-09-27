"""Thin wrapper around PyGithub. Everything GitHub-specific lives here."""
from datetime import timezone as dt_tz

from django.conf import settings
from github import Github

MAX_PATCH_CHARS = 8_000     # per file
MAX_FILES = 150
MAX_DIFF_CHARS = 120_000


def client() -> Github:
    return Github(settings.GITHUB_TOKEN or None, per_page=50)


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=dt_tz.utc)


def pr_to_dict(gh_pr) -> dict:
    files = []
    for f in list(gh_pr.get_files())[:MAX_FILES]:
        files.append(
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "patch": (f.patch or "")[:MAX_PATCH_CHARS],
            }
        )
    diff = "\n".join(f"--- a/{f['filename']}\n+++ b/{f['filename']}\n{f['patch']}" for f in files)
    state = "merged" if gh_pr.merged else gh_pr.state
    return {
        "number": gh_pr.number,
        "title": gh_pr.title or "",
        "body": gh_pr.body or "",
        "author": gh_pr.user.login if gh_pr.user else "",
        "state": state,
        "url": gh_pr.html_url,
        "additions": gh_pr.additions,
        "deletions": gh_pr.deletions,
        "changed_files": gh_pr.changed_files,
        "files": files,
        "diff": diff[:MAX_DIFF_CHARS],
        "opened_at": _aware(gh_pr.created_at),
        "merged_at": _aware(gh_pr.merged_at),
    }


def fetch_pr(full_name: str, number: int) -> dict:
    return pr_to_dict(client().get_repo(full_name).get_pull(number))


def iter_merged_prs(full_name: str, limit: int):
    """Yield up to `limit` merged PRs (newest first) as dicts."""
    seen = 0
    for gh_pr in client().get_repo(full_name).get_pulls(state="closed", sort="updated", direction="desc"):
        if not gh_pr.merged:
            continue
        yield pr_to_dict(gh_pr)
        seen += 1
        if seen >= limit:
            return
