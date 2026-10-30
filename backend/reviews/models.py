from django.db import models


class PullRequest(models.Model):
    repo = models.CharField(max_length=200)
    number = models.IntegerField()
    title = models.CharField(max_length=500)
    status = models.CharField(max_length=20, default="merged")
    merged_at = models.DateTimeField(null=True, blank=True)
    body = models.TextField(blank=True)
    diff = models.TextField(blank=True)
    files_changed = models.JSONField(default=list)
    additions = models.IntegerField(default=0)
    deletions = models.IntegerField(default=0)
    summary = models.TextField(blank=True)
    # Proxy ground truth from the labeling pipeline (reverted / hotfixed / bug-referenced).
    # Shown next to the predictions so reviewers can see what actually happened.
    actual_outcome = models.BooleanField(null=True, blank=True)

    class Meta:
        unique_together = ("repo", "number")
        ordering = ["-merged_at", "-id"]

    def __str__(self):
        return f"{self.repo}#{self.number}: {self.title}"


class Score(models.Model):
    METHODS = [
        ("rule_based", "Rule-based"),
        ("ml_based", "ML-based"),
        ("llm_based", "LLM-based"),
    ]
    pull_request = models.ForeignKey(PullRequest, related_name="scores", on_delete=models.CASCADE)
    method = models.CharField(max_length=20, choices=METHODS)
    score = models.IntegerField()               # 0-100
    label = models.CharField(max_length=10)     # low / medium / high
    reasons = models.JSONField(default=list)

    class Meta:
        unique_together = ("pull_request", "method")

    def __str__(self):
        return f"{self.pull_request} [{self.method}={self.score}]"


class Comment(models.Model):
    pull_request = models.ForeignKey(PullRequest, related_name="comments", on_delete=models.CASCADE)
    user = models.CharField(max_length=100, default="guest")   # becomes a real user after GitHub login (week 4)
    body = models.TextField()
    line_ref = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class EvaluationSnapshot(models.Model):
    """The latest comparison results (written by import_data from comparison_final.json)."""
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)