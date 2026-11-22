from django.utils.dateparse import parse_datetime

from .models import PullRequest, Score


def save_analysis(result):
    """Store a live analysis (from scoring.live.analyze_url) and return the PullRequest.

    Re-analysing a PR updates it in place; comments are kept. A PR that is already
    part of the evaluation dataset keeps source="dataset" and its actual_outcome."""
    rec = result["record"]
    fields = dict(
        title=rec["title"],
        status="merged" if rec["merged_at"] else "unmerged",
        merged_at=parse_datetime(rec["merged_at"] or rec["created_at"]),
        body=rec.get("body") or "",
        diff=rec.get("diff") or "",
        files_changed=[f["filename"] for f in rec["files"]],
        additions=rec["additions"],
        deletions=rec["deletions"],
        summary=result["summary"],
    )
    pr, created = PullRequest.objects.get_or_create(
        repo=rec["repo"], number=int(rec["number"]),
        defaults={**fields, "source": "live"})
    if not created:
        for key, value in fields.items():
            setattr(pr, key, value)
        pr.save()

    for method, s in result["scores"].items():
        Score.objects.update_or_create(
            pull_request=pr, method=method,
            defaults=dict(score=s["score"], label=s["label"], reasons=s["reasons"]))
    return pr