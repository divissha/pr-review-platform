import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleLogin() {
    setLoading(true);
    await login();
    navigate("/");
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white border border-gray-200 rounded-lg p-8 max-w-sm w-full text-center">
        <h1 className="text-xl font-bold text-gray-900 mb-2">
          PR Review Platform
        </h1>
        <p className="text-gray-500 text-sm mb-6">
          Sign in to view and analyze your pull requests.
        </p>
        <button
          onClick={handleLogin}
          disabled={loading}
          className="w-full bg-gray-900 text-white py-2.5 rounded-lg font-medium hover:bg-gray-700 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? "Signing in…" : "Sign in with GitHub"}
        </button>
      </div>
    </div>
  );
}