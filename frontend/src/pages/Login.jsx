import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Login() {
  const navigate = useNavigate();
  const [checking, setChecking] = useState(true);
  const error = new URLSearchParams(window.location.search).get("login_error");

  useEffect(() => {
    fetch(`${API}/api/auth/me/`, { credentials: "include" })
      .then((r) => r.json())
      .then((me) => {
        if (me.authenticated) navigate("/", { replace: true });
        else setChecking(false);
      })
      .catch(() => setChecking(false));
  }, [navigate]);

  if (checking) return <div className="p-8" style={{ color: "#656d76" }}>Loading…</div>;

  return (
    <div style={{ maxWidth: 440, margin: "72px auto", padding: "0 20px" }}>
      <div style={{ background: "#fff", border: "1px solid #d0d7de", borderRadius: 8, padding: 32 }}>
        <div style={{ fontSize: ".72rem", fontWeight: 600, letterSpacing: ".1em",
                      textTransform: "uppercase", color: "#0969da" }}>
          GitHub Pull Risk Analyzer
        </div>
        <div style={{ fontSize: "1.5rem", fontWeight: 700, margin: "8px 0 8px" }}>Sign in</div>
        <p style={{ color: "#656d76", fontSize: ".9rem", lineHeight: 1.6, margin: "0 0 24px" }}>
          Use your GitHub account to continue. Only your public profile (username and
          avatar) is read. No repository access is requested.
        </p>
        {error && (
          <p style={{ color: "#cf222e", fontSize: ".85rem", margin: "0 0 16px" }}>{error}</p>
        )}
        <a
          href={`${API}/api/auth/github/login/`}
          style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 10,
                   background: "#1f2328", color: "#fff", padding: "11px 16px", borderRadius: 6,
                   fontWeight: 600, fontSize: ".92rem", textDecoration: "none" }}
        >
          <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
          Continue with GitHub
        </a>
      </div>
    </div>
  );
}