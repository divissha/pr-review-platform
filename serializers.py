from rest_framework import serializers

from scoring.models import Analysis

from .models import Comment, PullRequest, Repository


class AnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analysis
        fields = ["method", "risk", "label", "summary", "reasons", "status", "error", "model_version", "latency_ms"]


class RepositorySerializer(serializers.ModelSerializer):
    pr_count = serializers.IntegerField(source="pull_requests.count", read_only=True)

    class Meta:
        model = Repository
        fields = ["id", "full_name", "is_demo", "pr_count"]


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "author", "body", "created_at"]
        read_only_fields = ["id", "created_at"]


class PullRequestListSerializer(serializers.ModelSerializer):
    repo = serializers.CharField(source="repo.full_name")
    analyses = AnalysisSerializer(many=True, read_only=True)

    class Meta:
        model = PullRequest
        fields = [
            "id", "repo", "number", "title", "author", "state", "url",
            "additions", "deletions", "changed_files", "opened_at", "outcome", "analyses",
        ]


class PullRequestDetailSerializer(PullRequestListSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta(PullRequestListSerializer.Meta):
        fields = PullRequestListSerializer.Meta.fields + ["body", "files", "diff", "comments"]
