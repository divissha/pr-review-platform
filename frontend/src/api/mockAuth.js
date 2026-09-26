// Mock GitHub OAuth — mirrors what the real Django OAuth endpoints will return.
// Swap the internals for real fetch calls once Person B's backend is ready.

const MOCK_USER = {
  id: 1,
  username: "yourname",
  avatar_url: "https://avatars.githubusercontent.com/u/0000000?v=4",
};

const delay = (ms = 300) => new Promise((res) => setTimeout(res, ms));

// GET /api/auth/me/
export async function getCurrentUser() {
  await delay();
  const stored = localStorage.getItem("mock_auth_user");
  return stored ? JSON.parse(stored) : null;
}

// Simulates clicking "Sign in with GitHub" and completing the OAuth flow
export async function login() {
  await delay(500);
  localStorage.setItem("mock_auth_user", JSON.stringify(MOCK_USER));
  return MOCK_USER;
}

// Simulates logging out
export async function logout() {
  await delay();
  localStorage.removeItem("mock_auth_user");
}

/*
  REAL VERSION (once Django backend is live):

  export async function getCurrentUser() {
    const res = await fetch(`${BASE_URL}/api/auth/me/`, { credentials: "include" });
    if (!res.ok) return null;
    return res.json();
  }

  export function login() {
    window.location.href = `${BASE_URL}/api/auth/github/login/`;
  }
*/