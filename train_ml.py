"""Train the ML scorer on labelled PRs using a TIME-BASED split (train on old, test on new)."""
from datetime import datetime

import joblib
from django.core.management.base import BaseCommand, CommandError
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from core.models import PullRequest
from scoring.features import FEATURE_NAMES, extract
from scoring.ml_based import ARTIFACT


class Command(BaseCommand):
    help = "Train logistic regression on labelled PRs; saves the model + the hold-out PR ids."

    def add_arguments(self, parser):
        parser.add_argument("--train-frac", type=float, default=0.7)
        parser.add_argument("--repo", default=None)

    def handle(self, *args, train_frac, repo, **opts):
        qs = PullRequest.objects.exclude(outcome="unknown").order_by("opened_at")
        if repo:
            qs = qs.filter(repo__full_name=repo)
        prs = list(qs)
        if len(prs) < 30:
            raise CommandError(f"Need >= 30 labelled PRs, found {len(prs)}. Run seed_demo or collect_prs first.")

        cut = int(len(prs) * train_frac)
        train, test = prs[:cut], prs[cut:]
        X = lambda rows: [[extract(p)[n] for n in FEATURE_NAMES] for p in rows]  # noqa: E731
        y = lambda rows: [int(p.is_risky) for p in rows]  # noqa: E731
        if len(set(y(train))) < 2:
            raise CommandError("Training split contains only one class - need more labelled data.")

        pipe = Pipeline([("scale", StandardScaler()),
                         ("clf", LogisticRegression(class_weight="balanced", max_iter=1000))])
        pipe.fit(X(train), y(train))

        self.stdout.write(f"train={len(train)} (risky {sum(y(train))})  test={len(test)} (risky {sum(y(test))})")
        if len(set(y(test))) == 2:
            proba = pipe.predict_proba(X(test))[:, 1]
            self.stdout.write(f"hold-out ROC-AUC={roc_auc_score(y(test), proba):.3f}  "
                              f"PR-AUC={average_precision_score(y(test), proba):.3f}")

        bundle = {"model": pipe, "features": FEATURE_NAMES,
                  "version": f"logreg-{datetime.now():%Y%m%d-%H%M}", "test_ids": [p.id for p in test]}
        joblib.dump(bundle, ARTIFACT)
        self.stdout.write(self.style.SUCCESS(f"Saved {ARTIFACT.name}. Next: python manage.py run_batch"))
