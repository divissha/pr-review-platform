"""
Week 1: score every labeled PR with the rule-based and ML methods and
compare them (plus a size-only baseline) on identical metrics.

Run from the backend/ folder:
    python -m scoring.run_week1
"""
import numpy as np
import pandas as pd

from scoring.evaluate import evaluate
from scoring.features import DATA_DIR, load_labeled_dataset
from scoring.ml_based import (FEATURES, build_models, cross_validated_scores,
                              make_matrix)
from scoring.rule_based import score_pr

RULE_THRESHOLD = 30   # flag "medium" or "high" as risky (set a priori)
ML_THRESHOLD = 0.5


def main():
    df = load_labeled_dataset()
    y = df["risky"].to_numpy()
    print(f"Usable PRs: {len(df)} | risky: {y.sum()} ({y.mean():.1%})")
    print(f"(A random scorer would get PR-AUC ~ {y.mean():.3f} and ROC-AUC 0.5)\n")

    results = {}
    per_pr = df[["repo", "number", "risky"]].copy()

    # ---- Method 1: rule-based (no training, so evaluate on everything) ----
    rule = [score_pr(row) for row in df.to_dict("records")]
    per_pr["rule_score"] = [r["score"] for r in rule]
    per_pr["rule_label"] = [r["label"] for r in rule]
    per_pr["rule_reasons"] = ["; ".join(r["reasons"]) for r in rule]
    results["rule_based"] = evaluate(y, per_pr["rule_score"], RULE_THRESHOLD)

    # ---- Baseline: "bigger change = riskier" ----
    results["size_only_baseline"] = evaluate(y, df["churn"])

    # ---- Method 2: ML, repeated stratified 5-fold cross-validation ----
    X = make_matrix(df)
    for name, model in build_models(y).items():
        runs = cross_validated_scores(model, X, y)
        metric_runs = pd.DataFrame(
            [evaluate(y, oof, ML_THRESHOLD) for oof in runs])
        results[name] = metric_runs.mean().to_dict()
        results[name + "_std"] = metric_runs.std().to_dict()
        per_pr[name + "_prob"] = np.mean(runs, axis=0)

    # ---- Report ----
    table = pd.DataFrame(results).T
    main_rows = [r for r in table.index if not r.endswith("_std")]
    print(table.loc[main_rows].round(3).to_string())
    print("\nML rows are means over 5 repeats of 5-fold CV; std across repeats:")
    print(table.loc[[r for r in table.index if r.endswith("_std")],
                    ["roc_auc", "pr_auc", "precision_top10", "recall_top10"]]
          .round(3).to_string())

    # Descriptive only: which features does the logistic model lean on?
    lr = build_models(y)["logistic_regression"].fit(X, y)
    coefs = pd.Series(lr[-1].coef_[0], index=FEATURES).sort_values()
    print("\nLogistic regression coefficients (standardised, fit on all data):")
    print(coefs.round(2).to_string())

    table.round(4).to_csv(DATA_DIR / "week1_results.csv")
    per_pr.to_csv(DATA_DIR / "scores_week1.csv", index=False)
    print(f"\nSaved {DATA_DIR / 'week1_results.csv'} and scores_week1.csv")


if __name__ == "__main__":
    main()