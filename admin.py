from django.contrib import admin

from .models import Analysis


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ("pr", "method", "risk", "label", "status", "latency_ms")
    list_filter = ("method", "status", "label")
