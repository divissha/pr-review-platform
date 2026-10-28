"""
Do we actually recognise reverts? Free check, no API calls.

build_dataset.py only treats a PR as a revert if its title STARTS with
"Revert". numpy writes "REV: ..." and "BUG: Revert ...", which would be missed.
This counts how many such PRs exist and how many point at a PR we have.

    python -m scoring.check_revert_coverage
"""
import json
import random
import re
from collections import defaultdict

from scoring.features import RAW_DIR, is_backport

REVERT_LIKE = re.compile(r"\brevert(s|ed)?\b|^\s*rev\s*:", re.I)
RECOGNISED = re.compile(r"^\s*revert", re.I)       # what build_dataset recognises today
REF = re.compile(r"(?:#|gh-)(\d{2,6})")


def main():
    by_repo = defaultdict(list)
    for path in sorted(RAW_DIR.glob("*.jsonl")):
        for line in open(path):
            r = json.loads(line)
            r.pop("diff", None)
            by_repo[r["repo"]].append(r)

    random.seed(0)
    for repo, prs in by_repo.items():
        have = {int(p["number"]) for p in prs}
        revert_like = [p for p in prs if REVERT_LIKE.search(p["title"]) and not is_backport(p)]
        recognised = [p for p in revert_like if RECOGNISED.match(p["title"])]
        missed = [p for p in revert_like if not RECOGNISED.match(p["title"])]

        def target_in_data(p):
            text = p["title"] + " " + (p.get("body") or "")[:300]
            return [int(n) for n in REF.findall(text)
                    if int(n) in have and int(n) != int(p["number"])]

        rec_hit = [p for p in recognised if target_in_data(p)]
        miss_hit = [p for p in missed if target_in_data(p)]
        print(f"\n{repo}: {len(prs)} PRs | revert-like titles: {len(revert_like)} "
              f"| recognised today: {len(recognised)} ({len(rec_hit)} point at a PR we have) "
              f"| MISSED: {len(missed)} ({len(miss_hit)} point at a PR we have)")
        for p in random.sample(miss_hit, min(6, len(miss_hit))):
            print(f"    missed: {p['title'][:75]}  -> {target_in_data(p)}")


if __name__ == "__main__":
    main()