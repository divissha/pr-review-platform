import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Set to true to force every page behind GitHub sign-in.
// Left false so the demo still works if GitHub or the network misbehaves.
const REQUIRE_LOGIN = false;

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (!REQUIRE_LOGIN) return children;
  if (loading) return <div className="p-8" style={{ color: "#656d76" }}>Loading…</div>;
  return user ? children : <Navigate to="/login" replace />;
}