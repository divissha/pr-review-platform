import os
from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import TestCase


class GithubAuthTests(TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {"GITHUB_CLIENT_ID": "cid", "GITHUB_CLIENT_SECRET": "sec"})
        p.start(); self.addCleanup(p.stop)

    def _start(self):
        r = self.client.get("/api/auth/github/login/")
        q = parse_qs(urlparse(r["Location"]).query)
        return r, q

    def test_login_redirects_to_github_with_state(self):
        r, q = self._start()
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].startswith("https://github.com/login/oauth/authorize"))
        self.assertEqual(q["client_id"], ["cid"])
        self.assertEqual(q["redirect_uri"], ["http://testserver/api/auth/github/callback/"])
        self.assertEqual(q["scope"], ["read:user"])
        self.assertEqual(q["state"][0], self.client.session["oauth_state"])

    def test_missing_client_id_is_reported_not_crashed(self):
        with mock.patch.dict(os.environ, {"GITHUB_CLIENT_ID": ""}):
            r = self.client.get("/api/auth/github/login/")
        self.assertIn("login_error=", r["Location"])

    def test_wrong_state_is_rejected(self):
        self._start()
        r = self.client.get("/api/auth/github/callback/?code=abc&state=forged")
        self.assertIn("login_error=", r["Location"])
        self.assertFalse(self.client.get("/api/auth/me/").json()["authenticated"])

    def test_full_login_logout(self):
        _, q = self._start()
        tok = mock.Mock(); tok.json.return_value = {"access_token": "t"}
        usr = mock.Mock(); usr.json.return_value = {"login": "octo", "name": "Octo Cat",
                                                    "avatar_url": "http://a/x.png"}
        with mock.patch("reviews.auth_github.requests.post", return_value=tok), \
             mock.patch("reviews.auth_github.requests.get", return_value=usr):
            r = self.client.get(f"/api/auth/github/callback/?code=abc&state={q['state'][0]}")
        self.assertEqual(r["Location"], "http://localhost:5173/")
        me = self.client.get("/api/auth/me/").json()
        self.assertEqual(me, {"authenticated": True, "login": "octo", "name": "Octo Cat",
                              "avatar_url": "http://a/x.png"})
        self.assertTrue(get_user_model().objects.filter(username="octo").exists())
        self.client.post("/api/auth/logout/")
        self.assertFalse(self.client.get("/api/auth/me/").json()["authenticated"])

    def test_github_refusing_the_code_is_reported(self):
        _, q = self._start()
        tok = mock.Mock(); tok.json.return_value = {"error": "bad_verification_code",
                                                    "error_description": "The code passed is incorrect"}
        with mock.patch("reviews.auth_github.requests.post", return_value=tok):
            r = self.client.get(f"/api/auth/github/callback/?code=abc&state={q['state'][0]}")
        self.assertIn("incorrect", r["Location"])

    def test_returning_user_is_not_duplicated(self):
        for _ in range(2):
            _, q = self._start()
            tok = mock.Mock(); tok.json.return_value = {"access_token": "t"}
            usr = mock.Mock(); usr.json.return_value = {"login": "octo"}
            with mock.patch("reviews.auth_github.requests.post", return_value=tok), \
                 mock.patch("reviews.auth_github.requests.get", return_value=usr):
                self.client.get(f"/api/auth/github/callback/?code=abc&state={q['state'][0]}")
        self.assertEqual(get_user_model().objects.filter(username="octo").count(), 1)