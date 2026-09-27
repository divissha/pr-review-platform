from django.db import models
from django.utils import timezone


class Repository(models.Model):
    full_name = models.CharField(max_length=200, unique=True)  # "owner/name"
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "repositories"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class PullRequest(models.Model):
    class Outcome(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        CLEAN = "clean", "Clean"
        REVERTED = "reverted", "Reverted"
        BUG_LINKED = "bug_linked", "Bug-linked"
        HOTFIXED = "hotfixed", "Hotfixed"

    RISKY_OUTCOMES = (Outcome.REVERTED, Outcome.BUG_LINKED, Outcome.HOTFIXED)

    repo = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name="pull_requests")
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=500)
    body = models.TextField(blank=True)
    author = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=20, default="open")  # open / closed / merged
    url = models.URLField(blank=True)

    additions = models.PositiveIntegerField(default=0)
    deletions = models.PositiveIntegerField(default=0)
    changed_files = models.PositiveIntegerField(default=0)
    files = models.JSONField(default=list, blank=True)  # [{filename,status,additions,deletions,patch}]
    diff = models.TextField(blank=True)

    opened_at = models.DateTimeField(default=timezone.now)
    merged_at = models.DateTimeField(null=True, blank=True)

    # Ground truth for batch evaluation
    outcome = models.CharField(max_length=20, choices=Outcome.choices, default=Outcome.UNKNOWN)
    is_historical = models.BooleanField(default=False)

    class Meta:
        unique_together = ("repo", "number")
        ordering = ["-opened_at"]

    def __str__(self):
        return f"{self.repo.full_name}#{self.number}"

    @property
    def is_risky(self) -> bool:
        return self.outcome in self.RISKY_OUTCOMES


class Comment(models.Model):
    pr = models.ForeignKey(PullRequest, on_delete=models.CASCADE, related_name="comments")
    author = models.CharField(max_length=100, default="anonymous")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
