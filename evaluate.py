"""Print the comparison table - the headline result of the project."""
from django.core.management.base import BaseCommand

from scoring.evaluation import evaluate


class Command(BaseCommand):
    help = "Precision / recall / F1 / AUC per scoring method vs real outcomes."

    def add_arguments(self, parser):
        parser.add_argument("--threshold", type=float, default=0.5)
        parser.add_argument("--repo", default=None)
        parser.add_argument("--all", action="store_true", help="include PRs the ML model trained on (optimistic!)")

    def handle(self, *args, threshold, repo, all, **opts):
        r = evaluate(threshold, repo, holdout_only=not all)
        scope = "hold-out PRs only" if r["holdout_only"] else "ALL labelled PRs (ML is optimistic here)"
        self.stdout.write(f"{scope}: {r['n_prs']} PRs, {r['n_risky']} risky, threshold {threshold}\n")
        self.stdout.write(f"{'method':<7}{'n':>5}{'prec':>8}{'recall':>8}{'f1':>8}{'roc_auc':>9}{'pr_auc':>8}")
        for m in r["methods"]:
            self.stdout.write(f"{m['method']:<7}{m['n']:>5}{m['precision']:>8}{m['recall']:>8}{m['f1']:>8}"
                              f"{str(m['roc_auc']):>9}{str(m['pr_auc']):>8}")
