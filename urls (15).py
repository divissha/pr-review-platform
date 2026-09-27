from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PullRequestViewSet, RepositoryViewSet
from .webhooks import github_webhook

router = DefaultRouter()
router.register("repos", RepositoryViewSet, basename="repo")
router.register("prs", PullRequestViewSet, basename="pr")

urlpatterns = [
    path("webhooks/github/", github_webhook, name="github-webhook"),
    path("", include(router.urls)),
]
