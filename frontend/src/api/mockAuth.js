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










// const MOCK_USER = {
//   id: 1,
//   username: "yourname",
//   avatar_url: "https://avatars.githubusercontent.com/u/0000000?v=4",
// };
// const delay = (ms = 300) => new Promise((res) => setTimeout(res, ms));

// export async function getCurrentUser() {
//   await delay();
//   const stored = localStorage.getItem("mock_auth_user");
//   return stored ? JSON.parse(stored) : null;
// }
// export async function login() {
//   await delay(500);
//   localStorage.setItem("mock_auth_user", JSON.stringify(MOCK_USER));
//   return MOCK_USER;
// }
// export async function logout() {
//   await delay();
//   localStorage.removeItem("mock_auth_user");
// }
// EOF

// cat > /home/claude/pr-review-frontend/src/context/AuthContext.jsx << 'EOF'
// import { createContext, useContext, useEffect, useState } from "react";
// import { getCurrentUser, login as apiLogin, logout as apiLogout } from "../api/mockAuth";

// const AuthContext = createContext(null);

// export function AuthProvider({ children }) {
//   const [user, setUser] = useState(null);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     getCurrentUser().then((u) => {
//       setUser(u);
//       setLoading(false);
//     });
//   }, []);

//   async function login() {
//     const u = await apiLogin();
//     setUser(u);
//   }
//   async function logout() {
//     await apiLogout();
//     setUser(null);
//   }

//   return (
//     <AuthContext.Provider value={{ user, loading, login, logout }}>
//       {children}
//     </AuthContext.Provider>
//   );
// }
// export function useAuth() {
//   return useContext(AuthContext);
// }
// EOF

// cat > /home/claude/pr-review-frontend/src/components/ProtectedRoute.jsx << 'EOF'
// import { Navigate } from "react-router-dom";
// import { useAuth } from "../context/AuthContext";

// export default function ProtectedRoute({ children }) {
//   const { user, loading } = useAuth();
//   if (loading) return <div className="p-8 text-dim font-mono text-sm">checking login…</div>;
//   if (!user) return <Navigate to="/login" replace />;
//   return children;
// }