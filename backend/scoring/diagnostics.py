"""
How much should we trust the week-1 numbers?

  1. Bootstrap 95% confidence intervals (only ~40 risky PRs, so numbers wobble)
  2. numpy vs the other repos (numpy holds most of the risky PRs)
  3. Which features differ between risky and safe PRs

Run from backend/ after run_week1:
    python -m scoring.diagnostics
"""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from scoring.evaluate import evaluate
from scoring.features import DATA_DIR, DATA_DIR, eligible_mask, load_labeled_dataset

N_BOOT = 1000


def main():
    feats = load_labeled_dataset()
    scores = pd.read_csv(DATA_DIR / "scores_week1.csv")
    df = feats.merge(scores.drop(columns=["risky"]), on=["repo", "number"])
    y = df["risky"].to_numpy()

    methods = {"rule_based": df["rule_score"], "size_only": df["churn"]}
    for col in df.columns:
        if col.endswith("_prob"):
            methods[col[:-5]] = df[col]

    # ---- 1. Bootstrap confidence intervals ----
    print(f"1) Bootstrap 95% CIs ({N_BOOT} resamples of the PRs)\n")
    rng = np.random.RandomState(0)
    rows = []
    for name, s in methods.items():
        s = s.to_numpy()
        stats = []
        for _ in range(N_BOOT):
            idx = rng.randint(0, len(y), len(y))
            if y[idx].sum() == 0:
                continue
            m = evaluate(y[idx], s[idx])
            stats.append([m["roc_auc"], m["pr_auc"], m["recall_top10"]])
        lo, hi = np.percentile(stats, [2.5, 97.5], axis=0)
        point = evaluate(y, s)
        rows.append({
            "method": name,
            "roc_auc": f"{point['roc_auc']:.3f} [{lo[0]:.3f}, {hi[0]:.3f}]",
            "pr_auc": f"{point['pr_auc']:.3f} [{lo[1]:.3f}, {hi[1]:.3f}]",
            "recall_top10": f"{point['recall_top10']:.3f} [{lo[2]:.3f}, {hi[2]:.3f}]",
        })
    print(pd.DataFrame(rows).to_string(index=False))

    # ---- 2. numpy vs everything else ----
    print("\n2) ROC-AUC by repo group (numpy holds most of the risky PRs)\n")
    groups = {"numpy only": df["repo"] == "numpy/numpy",
              "all other repos": df["repo"] != "numpy/numpy"}
    out = []
    for gname, mask in groups.items():
        sub_y = y[mask.to_numpy()]
        row = {"group": gname, "PRs": int(mask.sum()), "risky": int(sub_y.sum())}
        for name, s in methods.items():
            row[name] = round(roc_auc_score(sub_y, s[mask].to_numpy()), 3)
        out.append(row)
    print(pd.DataFrame(out).to_string(index=False))

    # ---- 3. Feature profile of risky vs safe PRs ----
    print("\n3) Share of PRs with each property (safe vs risky)\n")
    flags = pd.DataFrame({
        "touches_tests": df["touches_tests"],
        "source changed, no tests": df["src_no_tests"],
        "sensitive path": (df["sensitive_files"] > 0).astype(int),
        "native C/C++/Rust file": (df["native_files"] > 0).astype(int),
        "no source files at all": (df["n_source_files"] == 0).astype(int),
    })
    prof = flags.groupby(df["risky"]).mean().T
    prof.columns = ["safe", "risky"]
    print(prof.round(3).to_string())

    print("\nShare of PRs touching native files, per repo:")
    native = (df["native_files"] > 0).groupby(df["repo"]).mean().round(3)
    print(native.to_string())

        # ---- 4. Only PRs that actually change source code ----
    mask = eligible_mask(df).to_numpy()
    sub_y = y[mask]
    print(f"\n4) PRs that change source code: {int(mask.sum())} PRs, "
          f"{int(sub_y.sum())} risky (random baseline PR-AUC ~ {sub_y.mean():.3f})\n")
    rows = []
    for name, s in methods.items():
        m = evaluate(sub_y, s[mask].to_numpy())
        rows.append({"method": name, "roc_auc": round(m["roc_auc"], 3),
                     "pr_auc": round(m["pr_auc"], 3),
                     "recall_top10": round(m["recall_top10"], 3)})
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()