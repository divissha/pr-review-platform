from django.urls import path
from . import auth_github

from . import views

urlpatterns = [
    path("prs/", views.PullRequestList.as_view()),
    path("prs/<int:pk>/", views.PullRequestDetail.as_view()),
    path("prs/<int:pk>/comments/", views.CommentListCreate.as_view()),
    path("analyze/", views.analyze),
    path("evaluation/summary/", views.evaluation_summary),
    path("evaluation/prs/", views.evaluation_prs),
    path("auth/github/login/", auth_github.github_login),
    path("auth/github/callback/", auth_github.github_callback),
    path("auth/me/", auth_github.me),
    path("auth/logout/", auth_github.logout_view),
]