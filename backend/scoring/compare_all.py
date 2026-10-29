"""
Final comparison of all methods on the ELIGIBLE PRs (those that change source
code and are not docs/CI/typing/maintenance PRs), with honest uncertainty.

  - 95% bootstrap confidence intervals for each method
  - paired bootstrap differences: "is method A really better than method B?"
    (same resampled PRs for both, so the comparison is fair)

Works today with rule-based / ML / size-only. When data/scores_llm.csv exists
(after run_llm), the LLM is added automatically.

Run from backend/:
    python -m scoring.compare_all
"""
import itertools

import numpy as np
import pandas as pd

from scoring.evaluate import evaluate
from scoring.features import DATA_DIR, eligible_mask, load_labeled_dataset

N_BOOT = 2000
METRICS = ["roc_auc", "pr_auc", "recall_top10"]


def load_population():
    feats = load_labeled_dataset()
    feats = feats[eligible_mask(feats)]
    scores = pd.read_csv(DATA_DIR / "scores_week1.csv").drop(columns=["risky"])
    df = feats.merge(scores, on=["repo", "number"], how="inner")

    llm_path = DATA_DIR / "scores_llm.csv"
    if llm_path.exists():
        llm = pd.read_csv(llm_path)[["repo", "number", "llm_score"]]
        df = df.merge(llm, on=["repo", "number"], how="left")
        missing = int(df["llm_score"].isna().sum())
        if missing:
            print(f"[note] {missing} eligible PRs have no LLM score (failed calls); "
                  f"they are dropped for ALL methods so the comparison stays fair.")
            df = df.dropna(subset=["llm_score"])
    else:
        print("[note] data/scores_llm.csv not found: comparing the non-LLM methods only.")
    return df.reset_index(drop=True)


def method_scores(df):
    methods = {"rule_based": df["rule_score"], "size_only": df["churn"]}
    for col in df.columns:
        if col.endswith("_prob"):
            methods[col[:-5]] = df[col]
    if "llm_score" in df:
        methods["llm"] = df["llm_score"]
    return {k: v.to_numpy(dtype=float) for k, v in methods.items()}


def main():
    df = load_population()
    y = df["risky"].to_numpy().astype(int)
    methods = method_scores(df)
    print(f"\nEligible PRs: {len(df)} | risky: {y.sum()} ({y.mean():.1%}) "
          f"| random scorer: ROC-AUC 0.5, PR-AUC ~ {y.mean():.3f}, top-10% recall 10%\n")

    # ---- bootstrap: the SAME resampled PRs are used for every method ----
    rng = np.random.RandomState(0)
    draws = {m: [] for m in methods}
    kept = 0
    while kept < N_BOOT:
        idx = rng.randint(0, len(y), len(y))
        if y[idx].sum() == 0:
            continue
        for name, s in methods.items():
            r = evaluate(y[idx], s[idx])
            draws[name].append([r[m] for m in METRICS])
        kept += 1
    draws = {k: np.array(v) for k, v in draws.items()}

    # ---- 1. point estimates + 95% CIs ----
    rows = []
    for name, s in methods.items():
        point = evaluate(y, s)
        lo, hi = np.percentile(draws[name], [2.5, 97.5], axis=0)
        row = {"method": name}
        for i, m in enumerate(METRICS):
            row[m] = f"{point[m]:.3f} [{lo[i]:.3f}, {hi[i]:.3f}]"
        rows.append(row)
    table = pd.DataFrame(rows)
    print("1) Each method, with 95% bootstrap confidence intervals\n")
    print(table.to_string(index=False))

    # ---- 2. paired differences ----
    print("\n2) Paired comparison on ROC-AUC (A minus B). 'A better' = share of "
          "resamples where A beat B.\n   If the interval includes 0, you cannot "
          "claim a real difference.\n")
    pair_rows = []
    for a, b in itertools.combinations(methods, 2):
        diff = draws[a][:, 0] - draws[b][:, 0]
        lo, hi = np.percentile(diff, [2.5, 97.5])
        pair_rows.append({
            "A": a, "B": b,
            "diff": round(float(np.mean(diff)), 3),
            "95% CI": f"[{lo:.3f}, {hi:.3f}]",
            "A better": f"{(diff > 0).mean():.0%}",
            "verdict": ("A > B" if lo > 0 else "B > A" if hi < 0 else "no clear difference"),
        })
    pairs = pd.DataFrame(pair_rows)
    print(pairs.to_string(index=False))
    print(f"\n({len(pairs)} comparisons: at 95% expect about one to look 'significant' "
          f"by luck alone. Treat these as exploratory.)")

    table.to_csv(DATA_DIR / "comparison_final.csv", index=False)
    pairs.to_csv(DATA_DIR / "comparison_pairs.csv", index=False)
    print(f"\nSaved {DATA_DIR / 'comparison_final.csv'} and comparison_pairs.csv")


if __name__ == "__main__":
    main()