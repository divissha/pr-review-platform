from django.contrib import admin

from .models import Comment, EvaluationSnapshot, PullRequest, Score

admin.site.register(PullRequest)
admin.site.register(Score)
admin.site.register(Comment)
admin.site.register(EvaluationSnapshot)