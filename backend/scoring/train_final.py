"""
Train the final logistic-regression model on all usable PRs and save it, so a
brand-new PR can be scored live.

Run from backend/ (after run_week1, which writes the reference scores), using
the SAME virtualenv that runs the Django server:
    python -m scoring.train_final

Writes into data/models/:
    logistic_regression.joblib   the fitted model
    reference_probs.json         out-of-fold probabilities of the eligible PRs, used to
                                 turn a new PR's probability into a percentile (the same
                                 scale the dashboard already shows)
    training_keys.json           which PRs the model was trained on
    model_meta.json              the scikit-learn version that saved the model
"""
import json

import joblib
import pandas as pd
import sklearn

from scoring.features import DATA_DIR, eligible_mask, load_labeled_dataset
from scoring.ml_based import build_models, make_matrix

MODEL_DIR = DATA_DIR / "models"


def main():
    df = load_labeled_dataset()
    y = df["risky"].to_numpy()
    model = build_models(y)["logistic_regression"].fit(make_matrix(df), y)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_DIR / "logistic_regression.joblib")

    oof = pd.read_csv(DATA_DIR / "scores_week1.csv")[["repo", "number", "logistic_regression_prob"]]
    elig = df[eligible_mask(df)][["repo", "number"]].merge(oof, on=["repo", "number"])
    ref = sorted(float(p) for p in elig["logistic_regression_prob"])
    (MODEL_DIR / "reference_probs.json").write_text(json.dumps(ref))

    (MODEL_DIR / "model_meta.json").write_text(json.dumps({"sklearn": sklearn.__version__}))

    keys = [f"{r}#{n}" for r, n in zip(df["repo"], df["number"])]
    (MODEL_DIR / "training_keys.json").write_text(json.dumps(keys))
    print(f"Trained on {len(df)} PRs ({int(y.sum())} risky) with scikit-learn "
          f"{sklearn.__version__}. Reference distribution: {len(ref)} eligible PRs. "
          f"Saved to {MODEL_DIR}")


if __name__ == "__main__":
    main()