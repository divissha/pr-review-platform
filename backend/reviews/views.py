from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response

from scoring.live import AnalysisError, analyze_url

from .models import Comment, EvaluationSnapshot, PullRequest
from .serializers import (CommentSerializer, PullRequestDetailSerializer,
                          PullRequestListSerializer)
from .services import save_analysis


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
    serializer_class = PullRequestDetailSerializer
    queryset = PullRequest.objects.prefetch_related("scores")


class CommentListCreate(generics.ListCreateAPIView):
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


@api_view(["POST"])
def analyze(request):
    """POST /api/analyze/  {"url": "https://github.com/owner/repo/pull/123", "force": false}

    Fetches the PR from GitHub, scores it with all three methods and stores it.
    Takes roughly 10-40 seconds (mostly the LLM call)."""
    url = (request.data.get("url") or "").strip()
    if not url:
        return Response({"detail": "Provide a GitHub pull request URL."}, status=400)
    try:
        result = analyze_url(url, force=bool(request.data.get("force")))
    except AnalysisError as e:
        return Response({"detail": str(e)}, status=e.status)
    pr = save_analysis(result)
    data = PullRequestDetailSerializer(pr).data
    data["warnings"] = result["warnings"]
    return Response(data, status=201)


@api_view(["GET"])
def evaluation_summary(request):
    snap = EvaluationSnapshot.objects.order_by("-created_at").first()
    if snap is None:
        return Response(
            {"detail": "No evaluation loaded yet. Run: python manage.py import_data"},
            status=404)
    return Response(snap.data)


@api_view(["GET"])
def evaluation_prs(request):
    rows = []
    for pr in PullRequest.objects.prefetch_related("scores"):
        by = {s.method: s.score for s in pr.scores.all()}
        rows.append({"pr_id": pr.id, "actual_outcome": pr.actual_outcome,
                     "rule_based_score": by.get("rule_based"),
                     "ml_based_score": by.get("ml_based"),
                     "llm_based_score": by.get("llm_based")})
    return Response(rows)