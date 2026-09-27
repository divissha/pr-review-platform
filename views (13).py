from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import PullRequest, Repository
from .serializers import (
    CommentSerializer,
    PullRequestDetailSerializer,
    PullRequestListSerializer,
    RepositorySerializer,
)
from .tasks import analyze_pr_task, ingest_pr_task


class RepositoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    pagination_class = None


class PullRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET  /api/prs/?repo=&outcome=&state=&q=&ordering=
    GET  /api/prs/<id>/
    POST /api/prs/ingest/        {"repo": "owner/name", "number": 123}   (live mode, manual)
    POST /api/prs/<id>/analyze/  re-run scorers (optional {"methods": ["rule"]})
    GET/POST /api/prs/<id>/comments/
    """

    def get_queryset(self):
        qs = PullRequest.objects.select_related("repo").prefetch_related("analyses", "comments")
        p = self.request.query_params
        if p.get("repo"):
            qs = qs.filter(repo__full_name=p["repo"])
        if p.get("outcome"):
            qs = qs.filter(outcome=p["outcome"])
        if p.get("state"):
            qs = qs.filter(state=p["state"])
        if p.get("q"):
            qs = qs.filter(Q(title__icontains=p["q"]) | Q(author__icontains=p["q"]))
        ordering = p.get("ordering")
        if ordering in {"opened_at", "-opened_at", "additions", "-additions"}:
            qs = qs.order_by(ordering)
        return qs

    def get_serializer_class(self):
        return PullRequestDetailSerializer if self.action == "retrieve" else PullRequestListSerializer

    @action(detail=False, methods=["post"])
    def ingest(self, request):
        repo, number = request.data.get("repo"), request.data.get("number")
        if not repo or "/" not in str(repo) or not str(number).isdigit():
            return Response({"detail": "Send repo as 'owner/name' and number as an integer."}, status=400)
        ingest_pr_task.delay(repo, int(number))
        return Response({"queued": f"{repo}#{number}"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def analyze(self, request, pk=None):
        pr = self.get_object()
        methods = request.data.get("methods") or None
        analyze_pr_task.delay(pr.id, methods)
        return Response({"queued": pr.id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        pr = self.get_object()
        if request.method == "GET":
            return Response(CommentSerializer(pr.comments.all(), many=True).data)
        ser = CommentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(pr=pr)
        return Response(ser.data, status=status.HTTP_201_CREATED)
