import sys
import time

from github_client import get

for repo in sys.argv[1:]:
    revert = get("/search/issues", {"q": f"repo:{repo} is:pr is:merged Revert in:title", "per_page": 1}).json()["total_count"]
    time.sleep(2)  # the search API allows ~30 requests/minute
    total = get("/search/issues", {"q": f"repo:{repo} is:pr is:merged", "per_page": 1}).json()["total_count"]
    print(f"{repo}: {revert} revert PRs / {total} merged PRs ({revert / max(total, 1):.1%})")
    time.sleep(2)