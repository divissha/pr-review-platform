"""Method 1: transparent heuristics. Every point added is explained in `reasons`."""
from .base import BaseScorer, ScoreResult
from .features import extract


class RuleBasedScorer(BaseScorer):
    method = "rule"
    VERSION = "rules-v1"

    def score(self, pr) -> ScoreResult:
        f = extract(pr)
        churn = f["lines_added"] + f["lines_deleted"]
        reasons: list[str] = []

        if f["source_files"] == 0 and f["config_files"] == 0 and f["migration_files"] == 0:
            return ScoreResult(
                risk=0.03,
                summary=f"Touches only docs/tests ({f['files_changed']} files, {churn} lines).",
                reasons=["Docs/tests only, nothing that runs in production."],
                model_version=self.VERSION,
            )

        risk = 0.05
        if churn >= 1000:
            risk += 0.40; reasons.append(f"Very large change ({churn} lines).")
        elif churn >= 500:
            risk += 0.30; reasons.append(f"Large change ({churn} lines).")
        elif churn >= 200:
            risk += 0.20; reasons.append(f"Sizeable change ({churn} lines).")
        elif churn >= 50:
            risk += 0.08

        if f["files_changed"] > 30:
            risk += 0.15; reasons.append(f"Spread across {f['files_changed']} files.")
        elif f["files_changed"] > 15:
            risk += 0.10; reasons.append(f"Spread across {f['files_changed']} files.")

        if f["sensitive_files"]:
            risk += min(0.35, 0.25 + 0.05 * (f["sensitive_files"] - 1))
            reasons.append(f"Touches {f['sensitive_files']} sensitive file(s) (auth/payments/security).")
        if f["migration_files"]:
            risk += 0.10; reasons.append("Includes a database migration.")
        if f["config_files"]:
            risk += 0.08; reasons.append("Changes build/config/dependency files.")

        if f["test_files"] == 0 and churn >= 50:
            risk += 0.15; reasons.append("No tests added or changed.")
        elif f["test_files"]:
            risk -= 0.10; reasons.append("Tests were added or updated.")

        risk = max(0.0, min(1.0, risk))
        summary = (
            f"Changes {f['files_changed']} file(s) (+{f['lines_added']}/-{f['lines_deleted']}). "
            + (reasons[0] if reasons else "Small, low-impact change.")
        )
        return ScoreResult(risk=risk, summary=summary, reasons=reasons, model_version=self.VERSION)
