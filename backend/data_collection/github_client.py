import os
import time

import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException

load_dotenv()

BASE = "https://api.github.com"
TOKEN = os.getenv("GITHUB_TOKEN")

session = requests.Session()
session.headers.update({
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})
if TOKEN:
    session.headers["Authorization"] = f"Bearer {TOKEN}"


def get(url, params=None):
    """GET request with rate-limit handling and simple retries."""
    full_url = url if url.startswith("http") else BASE + url
    for attempt in range(6):
        try:
            resp = session.get(full_url, params=params, timeout=30)
        except RequestException as e:
            wait = min(2 ** attempt, 30)
            print(f"  Network error ({e}), retrying in {wait}s...")
            time.sleep(wait)
            continue
        if resp.status_code == 200:
            return resp

        # Secondary rate limit: GitHub tells us how long to wait
        if "Retry-After" in resp.headers:
            wait = int(resp.headers["Retry-After"]) + 1
            print(f"  Slow down requested, sleeping {wait}s...")
            time.sleep(wait)
            continue

        # Primary rate limit exhausted: sleep until the reset time
        if resp.status_code in (403, 429) and resp.headers.get("X-RateLimit-Remaining") == "0":
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - time.time(), 0) + 5
            print(f"  Rate limit hit, sleeping {int(wait)}s...")
            time.sleep(wait)
            continue

        if resp.status_code >= 500:
            time.sleep(2 ** attempt)
            continue

        resp.raise_for_status()

    raise RuntimeError(f"Failed after retries: {full_url}")


def paginate(url, params=None, max_items=None):
    """Follow GitHub's Link headers and collect all items (up to max_items)."""
    params = dict(params or {})
    params.setdefault("per_page", 100)
    items = []
    while url:
        resp = get(url, params)
        items.extend(resp.json())
        if max_items and len(items) >= max_items:
            return items[:max_items]
        url = resp.links.get("next", {}).get("url")
        params = None  # the "next" URL already carries its query string
    return items