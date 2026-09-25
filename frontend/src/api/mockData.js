// Mock data shaped exactly like the real Django API responses will be.
// Once the backend is ready, only mockApi.js needs to change — components stay the same.

export const mockPRs = [
  {
    id: 12,
    repo: "myorg/backend",
    pr_number: 42,
    title: "Add two-factor auth to login",
    status: "open",
    created_at: "2026-09-20T14:00:00Z",
    overall_risk: "medium",
  },
  {
    id: 13,
    repo: "myorg/backend",
    pr_number: 43,
    title: "Fix typo in README",
    status: "merged",
    created_at: "2026-09-19T09:30:00Z",
    overall_risk: "low",
  },
  {
    id: 14,
    repo: "myorg/frontend",
    pr_number: 88,
    title: "Refactor payment checkout flow",
    status: "open",
    created_at: "2026-09-21T11:15:00Z",
    overall_risk: "high",
  },
];

export const mockPRDetail = {
  12: {
    id: 12,
    repo: "myorg/backend",
    pr_number: 42,
    title: "Add two-factor auth to login",
    status: "open",
    diff: `diff --git a/auth.py b/auth.py
@@ -12,6 +12,18 @@ def login(request):
     user = authenticate(request)
+    if user.two_factor_enabled:
+        code = request.POST.get("totp_code")
+        if not verify_totp(user, code):
+            return HttpResponseForbidden("Invalid 2FA code")
     login_user(request, user)
     return redirect("dashboard")`,
    files_changed: ["auth.py", "views.py"],
    summary:
      "This PR adds 2FA support to the login flow using TOTP codes.",
    scores: {
      rule_based: {
        score: 62,
        label: "medium",
        reasons: ["touches auth.py", "no new tests"],
      },
      ml_based: {
        score: 71,
        label: "medium",
        reasons: ["similar to past risky PRs"],
      },
      llm_based: {
        score: 80,
        label: "high",
        reasons: [
          "security-sensitive change",
          "missing error handling on token validation",
        ],
      },
    },
  },
};

export const mockComments = {
  12: [
    {
      id: 5,
      user: "yourname",
      body: "Should we add rate limiting here too?",
      line_ref: 34,
      created_at: "2026-09-21T09:00:00Z",
    },
  ],
};

export const mockEvaluationSummary = {
  dataset_size: 320,
  metrics: {
    rule_based: { precision: 0.58, recall: 0.51, f1: 0.54 },
    ml_based: { precision: 0.71, recall: 0.66, f1: 0.68 },
    llm_based: { precision: 0.77, recall: 0.74, f1: 0.75 },
  },
};
