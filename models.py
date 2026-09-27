from django.db import models


class Analysis(models.Model):
    """One scorer's verdict on one PR. Exactly one row per (pr, method)."""

    class Method(models.TextChoices):
        RULE = "rule", "Rule-based"
        ML = "ml", "ML-based"
        LLM = "llm", "LLM-based"

    class Status(models.TextChoices):
        OK = "ok", "OK"
        UNAVAILABLE = "unavailable", "Unavailable"  # e.g. no API key, model not trained
        ERROR = "error", "Error"

    pr = models.ForeignKey("core.PullRequest", on_delete=models.CASCADE, related_name="analyses")
    method = models.CharField(max_length=10, choices=Method.choices)
    risk = models.FloatField(null=True, blank=True)  # 0.0 (safe) .. 1.0 (very risky)
    label = models.CharField(max_length=10, blank=True)  # low / medium / high
    summary = models.TextField(blank=True)
    reasons = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OK)
    error = models.TextField(blank=True)
    model_version = models.CharField(max_length=100, blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("pr", "method")
        ordering = ["method"]
        verbose_name_plural = "analyses"

    def __str__(self):
        return f"{self.pr} [{self.method}] {self.risk}"
