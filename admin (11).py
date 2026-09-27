from django.contrib import admin

from .models import Comment, PullRequest, Repository


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ("full_name", "is_demo", "created_at")


@admin.register(PullRequest)
class PullRequestAdmin(admin.ModelAdmin):
    list_display = ("__str__", "title", "outcome", "additions", "deletions", "is_historical")
    list_filter = ("repo", "outcome", "is_historical")
    search_fields = ("title", "author")


admin.site.register(Comment)
