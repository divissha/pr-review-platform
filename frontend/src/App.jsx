import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import PRList from "./pages/PRList";
import PRDetail from "./pages/PRDetail";
import Evaluation from "./pages/Evaluation";
import Login from "./pages/Login";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";

function Nav() {
  const { user, logout } = useAuth();
  return (
    <nav className="border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <div className="flex gap-6">
        <Link to="/" className="font-semibold text-gray-900">
          PR Review Platform
        </Link>
        <Link to="/" className="text-gray-600 hover:text-gray-900">
          Pull Requests
        </Link>
        <Link to="/evaluation" className="text-gray-600 hover:text-gray-900">
          Evaluation
        </Link>
      </div>
      {user && (
        <div className="flex items-center gap-3">
          <img src={user.avatar_url} alt="" className="w-6 h-6 rounded-full" />
          <span className="text-sm text-gray-700">{user.username}</span>
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-gray-900"
          >
            Log out
          </button>
        </div>
      )}
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <PRList />
            </ProtectedRoute>
          }
        />
        <Route
          path="/prs/:id"
          element={
            <ProtectedRoute>
              <PRDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/evaluation"
          element={
            <ProtectedRoute>
              <Evaluation />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}