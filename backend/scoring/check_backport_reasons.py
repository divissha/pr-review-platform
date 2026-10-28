"""For PRs flagged as backports WITHOUT a visible cue in the title, show why."""
import json
import random

import pandas as pd

from scoring.features import (BACKPORT_BODY_RE, BACKPORT_TITLE_SUFFIX_RE,
                              BACKPORT_TITLE_WORD_RE, DATASET_PATH, RAW_DIR,
                              is_backport)


def reason(pr):
    title, body = pr.get("title", ""), (pr.get("body") or "")[:300]
    if BACKPORT_TITLE_SUFFIX_RE.search(title):
        return "title ends with (#N)"
    if BACKPORT_TITLE_WORD_RE.search(title):
        return "title says backport"
    if BACKPORT_BODY_RE.match(body):
        return "description starts with backport/cherry-pick"
    return None


def main():
    labels = pd.read_csv(DATASET_PATH)
    usable = labels[labels["label_window_complete"] & ~labels["is_revert_pr"]]
    keys = set(zip(usable["repo"], usable["number"].astype(int)))
    counts, body_only = {}, []
    for path in RAW_DIR.glob("*.jsonl"):
        for line in open(path):
            r = json.loads(line)
            if (r["repo"], int(r["number"])) not in keys or not is_backport(r):
                continue
            why = reason(r)
            counts[why] = counts.get(why, 0) + 1
            if why.startswith("description"):
                body_only.append((r["title"], " ".join((r.get("body") or "")[:200].split())[:110]))
    print("Why PRs were flagged:")
    for why, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {why}")
    random.seed(1)
    print("\nSAMPLE flagged ONLY because of the description (title had no cue):")
    for title, body in random.sample(body_only, min(15, len(body_only))):
        print(f"  - {title[:70]}\n      body: {body}")


if __name__ == "__main__":
    main()