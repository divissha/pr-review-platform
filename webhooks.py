import hashlib
import hmac
import json

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .tasks import ingest_pr_task

HANDLED_ACTIONS = {"opened", "reopened", "synchronize", "ready_for_review"}


def _valid_signature(request) -> bool:
    secret = settings.GITHUB_WEBHOOK_SECRET
    if not secret:
        return settings.DEBUG  # no secret configured: only OK in local dev
    expected = "sha256=" + hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(request.headers.get("X-Hub-Signature-256", ""), expected)


@csrf_exempt
@require_POST
def github_webhook(request):
    """Receives PR events, answers fast, and lets Celery do the heavy work."""
    if not _valid_signature(request):
        return HttpResponseForbidden("invalid signature")

    event = request.headers.get("X-GitHub-Event", "")
    if event == "ping":
        return JsonResponse({"msg": "pong"})
    if event != "pull_request":
        return JsonResponse({"ignored": event}, status=200)

    try:
        payload = json.loads(request.body)
        action = payload["action"]
        full_name = payload["repository"]["full_name"]
        number = payload["pull_request"]["number"]
    except (ValueError, KeyError):
        return HttpResponseBadRequest("malformed payload")

    if action not in HANDLED_ACTIONS:
        return JsonResponse({"ignored": action}, status=200)

    # Re-delivery is safe: ingest is an upsert and analyses are update_or_create.
    ingest_pr_task.delay(full_name, number)
    return JsonResponse({"queued": f"{full_name}#{number}"}, status=202)
