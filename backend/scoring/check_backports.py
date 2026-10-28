import json, random
import pandas as pd
from scoring.features import DATASET_PATH, RAW_DIR, is_backport

labels = pd.read_csv(DATASET_PATH)
usable = labels[labels["label_window_complete"] & ~labels["is_revert_pr"]]
keys = set(zip(usable["repo"], usable["number"].astype(int)))
flagged, kept_suspect = [], []
for path in RAW_DIR.glob("*.jsonl"):
    for line in open(path):
        r = json.loads(line)
        if (r["repo"], int(r["number"])) not in keys:
            continue
        if is_backport(r):
            flagged.append(r["title"])
        elif "#" in r["title"] or "port" in r["title"].lower():
            kept_suspect.append(r["title"])
random.seed(0)
print(f"flagged as backport: {len(flagged)} | kept but title has '#' or 'port': {len(kept_suspect)}")
print("\nSAMPLE of titles EXCLUDED as backports:")
for t in random.sample(flagged, min(15, len(flagged))): print("  -", t[:90])
print("\nSAMPLE of titles KEPT that contain '#' or 'port' (look for missed backports):")
for t in random.sample(kept_suspect, min(15, len(kept_suspect))): print("  -", t[:90])