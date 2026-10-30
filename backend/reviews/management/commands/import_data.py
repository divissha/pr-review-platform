"""
Load PRs, scores and the evaluation results from backend/data into the database.

    python manage.py import_data            # eligible PRs only (the evaluation set)
    python manage.py import_data --all      # every usable PR

Safe to re-run (e.g. after the LLM scores arrive): PRs and scores are updated in
place, and user comments are never deleted.
"""
import json

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_datetime

from reviews.models import EvaluationSnapshot, PullRequest, Score
from scoring.features import (DATA_DIR, eligible_mask, iter_raw_records,
                              load_labeled_dataset)
from scoring.llm_based import DEFAULT_MODEL, load_cached
from scoring.rule_based import score_pr


def percentile_label(pct):
    return "high" if pct >= 90 else "medium" if pct >= 70 else "low"


class Command(BaseCommand):
    help = "Load PRs, scores and evaluation results from backend/data into the database"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true",
                            help="import every usable PR, not only the eligible ones")
        parser.add_argument("--llm-model", default=DEFAULT_MODEL)

    def handle(self, *args, **opts):
        df = load_labeled_dataset()
        if not opts["all"]:
            df = df[eligible_mask(df)]
        df = df.reset_index(drop=True)

        # ML scores come from run_week1 (out-of-fold probabilities, logistic regression)
        ml_path = DATA_DIR / "scores_week1.csv"
        if ml_path.exists():
            ml = pd.read_csv(ml_path)[["repo", "number", "logistic_regression_prob"]]
            df = df.merge(ml, on=["repo", "number"], how="left")
            df["ml_pct"] = df["logistic_regression_prob"].rank(pct=True) * 100
        else:
            self.stdout.write(self.style.WARNING("scores_week1.csv not found: no ML scores."))
            df["ml_pct"] = float("nan")

        keys = {(r, int(n)) for r, n in zip(df["repo"], df["number"])}
        records = {(r["repo"], int(r["number"])): r for r in iter_raw_records(keys)}

        n_pr = n_llm = 0
        with transaction.atomic():
            for row in df.to_dict("records"):
                rec = records.get((row["repo"], int(row["number"])))
                if rec is None:
                    continue

                llm = load_cached(opts["llm_model"], rec)
                summary = (llm["summary"] if llm else
                           f"{rec['changed_files']} files changed "
                           f"(+{rec['additions']}/-{rec['deletions']}). "
                           f"No LLM summary available yet.")

                pr, _ = PullRequest.objects.update_or_create(
                    repo=rec["repo"], number=int(rec["number"]),
                    defaults=dict(
                        title=rec["title"], status="merged",
                        merged_at=parse_datetime(rec["merged_at"]),
                        body=rec.get("body") or "", diff=rec.get("diff") or "",
                        files_changed=[f["filename"] for f in rec["files"]],
                        additions=rec["additions"], deletions=rec["deletions"],
                        summary=summary, actual_outcome=bool(row["risky"])))

                rule = score_pr(row)
                Score.objects.update_or_create(
                    pull_request=pr, method="rule_based",
                    defaults=dict(score=rule["score"], label=rule["label"],
                                  reasons=rule["reasons"]))

                if pd.notna(row["ml_pct"]):
                    pct = float(row["ml_pct"])
                    top = max(1, round(100 - pct))
                    Score.objects.update_or_create(
                        pull_request=pr, method="ml_based",
                        defaults=dict(score=int(round(pct)), label=percentile_label(pct),
                                      reasons=[f"ranked in the top {top}% of PRs by the "
                                               f"logistic-regression risk model"]))

                if llm:
                    Score.objects.update_or_create(
                        pull_request=pr, method="llm_based",
                        defaults=dict(score=llm["score"], label=llm["label"],
                                      reasons=llm["reasons"]))
                    n_llm += 1
                n_pr += 1

            eval_path = DATA_DIR / "comparison_final.json"
            if eval_path.exists():
                EvaluationSnapshot.objects.all().delete()
                EvaluationSnapshot.objects.create(data=json.loads(eval_path.read_text()))
                self.stdout.write("Loaded evaluation results.")
            else:
                self.stdout.write(self.style.WARNING(
                    "comparison_final.json not found: run `python -m scoring.compare_all` first."))

        self.stdout.write(self.style.SUCCESS(
            f"Imported {n_pr} PRs ({n_llm} with LLM scores)."))