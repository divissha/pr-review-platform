"""
Sign in with GitHub (OAuth 2.0 authorization-code flow).

  GET  /api/auth/github/login/     -> redirects the browser to GitHub
  GET  /api/auth/github/callback/  -> GitHub sends the user back here with ?code=...
  GET  /api/auth/me/               -> who is logged in (or authenticated: false)
  POST /api/auth/logout/           -> ends the session

Needs GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in backend/.env. We only ask GitHub
for the user's public profile (no repository access) and keep no GitHub token.
"""
import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

try:  # make sure backend/.env is read even if settings.py doesn't load it
    from dotenv import load_dotenv
    load_dotenv(Path(settings.BASE_DIR) / ".env")
except Exception:  # noqa: BLE001
    pass

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_URL = "https://api.github.com/user"
CALLBACK_PATH = "/api/auth/github/callback/"


def _frontend():
    return getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")


def _back(error=None):
    """Send the browser back to the React app, optionally with an error code."""
    url = _frontend() + "/"
    if error:
        url += "?" + urlencode({"login_error": error})
    return HttpResponseRedirect(url)


@require_GET
def github_login(request):
    client_id = os.environ.get("GITHUB_CLIENT_ID", "")
    if not client_id:
        return _back("GITHUB_CLIENT_ID is missing from backend/.env")
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state          # checked again in the callback (CSRF guard)
    params = {
        "client_id": client_id,
        "redirect_uri": request.build_absolute_uri(CALLBACK_PATH),
        "scope": "read:user",
        "state": state,
    }
    return HttpResponseRedirect(f"{AUTHORIZE_URL}?{urlencode(params)}")


@require_GET
def github_callback(request):
    if request.GET.get("error"):
        return _back(request.GET.get("error_description") or request.GET["error"])
    expected = request.session.pop("oauth_state", None)
    if not expected or request.GET.get("state") != expected:
        return _back("Login session expired or was tampered with. Please try again.")
    code = request.GET.get("code")
    if not code:
        return _back("GitHub did not return a login code.")

    try:
        tok = requests.post(
            TOKEN_URL,
            data={"client_id": os.environ.get("GITHUB_CLIENT_ID", ""),
                  "client_secret": os.environ.get("GITHUB_CLIENT_SECRET", ""),
                  "code": code,
                  "redirect_uri": request.build_absolute_uri(CALLBACK_PATH)},
            headers={"Accept": "application/json"}, timeout=15).json()
        access = tok.get("access_token")
        if not access:
            return _back(tok.get("error_description") or "GitHub refused the login code.")
        gh = requests.get(USER_URL, headers={"Authorization": f"Bearer {access}",
                                             "Accept": "application/vnd.github+json"},
                          timeout=15).json()
    except requests.RequestException as e:
        return _back(f"Could not reach GitHub: {e}")

    if not gh.get("login"):
        return _back("GitHub did not return a user profile.")

    user, _ = get_user_model().objects.get_or_create(username=gh["login"])
    if not user.first_name and gh.get("name"):
        user.first_name = gh["name"][:150]
        user.save(update_fields=["first_name"])
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session["gh_avatar"] = gh.get("avatar_url", "")
    return _back()


@require_GET
def me(request):
    u = request.user
    if not u.is_authenticated:
        return JsonResponse({"authenticated": False})
    return JsonResponse({"authenticated": True, "login": u.username,
                         "name": u.first_name or u.username,
                         "avatar_url": request.session.get("gh_avatar", "")})


@csrf_exempt
@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"authenticated": False})