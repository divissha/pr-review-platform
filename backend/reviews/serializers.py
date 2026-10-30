from rest_framework import serializers

from .models import Comment, PullRequest

RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


class PullRequestListSerializer(serializers.ModelSerializer):
    pr_number = serializers.IntegerField(source="number")
    created_at = serializers.DateTimeField(source="merged_at")
    overall_risk = serializers.SerializerMethodField()

    class Meta:
        model = PullRequest
        fields = ["id", "repo", "pr_number", "title", "status", "created_at", "overall_risk"]

    def get_overall_risk(self, obj):
        """Highest risk level any method assigned (a conservative flag)."""
        labels = [s.label for s in obj.scores.all()]  # prefetched in the view
        return max(labels, key=RISK_ORDER.get) if labels else None


class PullRequestDetailSerializer(serializers.ModelSerializer):
    pr_number = serializers.IntegerField(source="number")
    scores = serializers.SerializerMethodField()

    class Meta:
        model = PullRequest
        fields = ["id", "repo", "pr_number", "title", "status", "diff", "files_changed",
                  "additions", "deletions", "summary", "actual_outcome", "scores"]

    def get_scores(self, obj):
        return {s.method: {"score": s.score, "label": s.label, "reasons": s.reasons}
                for s in obj.scores.all()}


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "user", "body", "line_ref", "created_at"]
        read_only_fields = ["id", "created_at"]