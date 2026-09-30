"""
Step 1: download merged PRs (metadata + diff) from public GitHub repos.

Usage (run from the backend/ folder):
    python data_collection/collect_prs.py --repos pallets/flask pytest-dev/pytest --n 300

Output: backend/data/raw/<owner>__<repo>.jsonl  (one PR per line)
Safe to re-run: PRs already downloaded are skipped.
"""
import argparse
import json
from pathlib import Path

from github_client import get, paginate

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
MAX_DIFF_CHARS = 100_000  # cap per PR so files stay a sane size


def is_bot(pr):
    user = pr.get("user") or {}
    return user.get("type") == "Bot" or user.get("login", "").endswith("[bot]")


def list_merged_prs(repo, n):
    """Newest-first merged, non-bot PRs. The list endpoint also returns
    closed-but-unmerged PRs, so we filter those out."""
    merged = []
    url = f"/repos/{repo}/pulls"
    params = {"state": "closed", "sort": "created", "direction": "desc", "per_page": 100}
    while url and len(merged) < n:
        resp = get(url, params)
        for pr in resp.json():
            if pr.get("merged_at") and not is_bot(pr):
                merged.append(pr)
                if len(merged) >= n:
                    break
        url = resp.links.get("next", {}).get("url")
        params = None
    return merged


def list_revert_prs(repo, n):
    """Search API: merged PRs with 'revert' in the title, most recent first.
    Note: the search endpoint wraps results as {"items": [...]}, unlike the
    normal list endpoints, so it needs its own pagination loop."""
    results = []
    url = "/search/issues"
    params = {
        "q": f"repo:{repo} is:pr is:merged revert in:title",
        "sort": "created",
        "order": "desc",
        "per_page": 100,
    }
    while url and len(results) < n:
        resp = get(url, params)
        results.extend(resp.json()["items"])
        url = resp.links.get("next", {}).get("url")
        params = None
    return [{"number": i["number"]} for i in results[:n]]


def fetch_record(repo, summary):
    number = summary["number"]
    detail = get(f"/repos/{repo}/pulls/{number}").json()
    files = paginate(f"/repos/{repo}/pulls/{number}/files", max_items=300)
    diff = "\n".join(f"--- {f['filename']}\n{f.get('patch', '')}" for f in files)
    return {
        "repo": repo,
        "number": number,
        "title": detail["title"],
        "body": (detail.get("body") or "")[:5000],
        "author": (detail.get("user") or {}).get("login"),
        "created_at": detail["created_at"],
        "merged_at": detail["merged_at"],
        "additions": detail["additions"],
        "deletions": detail["deletions"],
        "changed_files": detail["changed_files"],
        "commits": detail["commits"],
        "comments": detail["comments"],
        "review_comments": detail["review_comments"],
        "files": [
            {
                "filename": f["filename"],
                "status": f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
            }
            for f in files
        ],
        "diff": diff[:MAX_DIFF_CHARS],
    }


def collect(repo, n, n_reverts=100):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / (repo.replace("/", "__") + ".jsonl")

    done = set()
    if out_path.exists():
        with open(out_path) as f:
            done = {json.loads(line)["number"] for line in f if line.strip()}

    print(f"[{repo}] listing merged PRs...")
    summaries = list_merged_prs(repo, n)
    print(f"[{repo}] listing revert PRs...")
    reverts = list_revert_prs(repo, n_reverts)

    seen = {s["number"] for s in summaries}
    all_summaries = summaries + [r for r in reverts if r["number"] not in seen]
    todo = [s for s in all_summaries if s["number"] not in done]
    print(f"[{repo}] {len(summaries)} recent + {len(reverts)} reverts = {len(all_summaries)} total, "
          f"{len(done)} already saved, {len(todo)} to download")

    with open(out_path, "a") as f:
        for i, s in enumerate(todo, 1):
            f.write(json.dumps(fetch_record(repo, s)) + "\n")
            f.flush()
            if i % 25 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", nargs="+", required=True, help="e.g. pallets/flask")
    parser.add_argument("--n", type=int, default=300, help="merged PRs per repo")
    args = parser.parse_args()
    for repo in args.repos:
        collect(repo, args.n)
