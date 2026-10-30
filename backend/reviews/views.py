from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Comment, EvaluationSnapshot, PullRequest
from .serializers import (CommentSerializer, PullRequestDetailSerializer,
                          PullRequestListSerializer)


class PullRequestList(generics.ListAPIView):
    """GET /api/prs/  (optional: ?repo=owner/name  ?search=text)"""
    serializer_class = PullRequestListSerializer

    def get_queryset(self):
        qs = PullRequest.objects.prefetch_related("scores")
        repo = self.request.query_params.get("repo")
        search = self.request.query_params.get("search")
        if repo:
            qs = qs.filter(repo=repo)
        if search:
            qs = qs.filter(title__icontains=search)
        return qs


class PullRequestDetail(generics.RetrieveAPIView):
    """GET /api/prs/<id>/"""
    serializer_class = PullRequestDetailSerializer
    queryset = PullRequest.objects.prefetch_related("scores")


class CommentListCreate(generics.ListCreateAPIView):
    """GET / POST /api/prs/<id>/comments/"""
    serializer_class = CommentSerializer

    def get_queryset(self):
        return Comment.objects.filter(pull_request_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        pr = get_object_or_404(PullRequest, pk=self.kwargs["pk"])
        user = self.request.user.username if self.request.user.is_authenticated else None
        if user:
            serializer.save(pull_request=pr, user=user)
        else:
            serializer.save(pull_request=pr)


@api_view(["GET"])
def evaluation_summary(request):
    """GET /api/evaluation/summary/ - the latest three-way comparison."""
    snap = EvaluationSnapshot.objects.order_by("-created_at").first()
    if snap is None:
        return Response(
            {"detail": "No evaluation loaded yet. Run: python manage.py import_data"},
            status=404)
    return Response(snap.data)


@api_view(["GET"])
def evaluation_prs(request):
    """GET /api/evaluation/prs/ - per-PR scores next to what actually happened."""
    rows = []
    for pr in PullRequest.objects.prefetch_related("scores"):
        by = {s.method: s.score for s in pr.scores.all()}
        rows.append({
            "pr_id": pr.id,
            "actual_outcome": pr.actual_outcome,
            "rule_based_score": by.get("rule_based"),
            "ml_based_score": by.get("ml_based"),
            "llm_based_score": by.get("llm_based"),
        })
    return Response(rows)