"""
Method 2: machine-learning risk scorer (Logistic Regression + XGBoost).

Features are only those knowable at merge time. Deliberately excluded:
  - `comments`: issue comments can be posted after the merge ("this broke X"),
    which would leak the outcome.
  - repo name / author: would let the model memorise project base rates.
"""
import numpy as np
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:  # XGBoost is optional; the script still runs without it
    from xgboost import XGBClassifier
except Exception:  # ImportError, or a missing libomp on macOS
    XGBClassifier = None

COUNT_COLS = ["additions", "deletions", "changed_files", "commits",
              "review_comments", "n_source_files", "sensitive_files",
              "native_files"]
FLAG_COLS = ["touches_tests", "src_no_tests", "config_change",
             "dependency_change"]
FEATURES = COUNT_COLS + FLAG_COLS


def make_matrix(df):
    """log1p the heavy-tailed counts; flags stay 0/1."""
    X = df[FEATURES].astype(float).copy()
    X[COUNT_COLS] = np.log1p(X[COUNT_COLS])
    return X


def build_models(y):
    models = {
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(class_weight="balanced", C=0.5, max_iter=2000),
        )
    }
    if XGBClassifier is not None:
        pos = max(1, int(np.sum(y)))
        neg = len(y) - pos
        models["xgboost"] = XGBClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            scale_pos_weight=float(np.sqrt(neg / pos)),  # softened imbalance weight
            eval_metric="logloss", random_state=0, n_jobs=1,
        )
    return models


def cross_validated_scores(model, X, y, n_splits=5, n_repeats=5):
    """Out-of-fold risk probabilities, repeated with different shuffles.
    Every PR is always scored by a model that never saw it in training."""
    runs = []
    for r in range(n_repeats):
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=r)
        oof = np.zeros(len(y))
        for train, test in skf.split(X, y):
            m = clone(model)
            m.fit(X.iloc[train], y[train])
            oof[test] = m.predict_proba(X.iloc[test])[:, 1]
        runs.append(oof)
    return runs