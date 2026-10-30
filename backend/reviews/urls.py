from django.urls import path

from . import views

urlpatterns = [
    path("prs/", views.PullRequestList.as_view()),
    path("prs/<int:pk>/", views.PullRequestDetail.as_view()),
    path("prs/<int:pk>/comments/", views.CommentListCreate.as_view()),
    path("evaluation/summary/", views.evaluation_summary),
    path("evaluation/prs/", views.evaluation_prs),
]