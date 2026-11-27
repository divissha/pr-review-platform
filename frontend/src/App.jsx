import { BrowserRouter, Routes, Route, NavLink, Link } from "react-router-dom";
import PRList from "./pages/PRList";
import PRDetail from "./pages/PRDetail";
import Evaluation from "./pages/Evaluation";
import Login from "./pages/Login";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";

function Nav() {
  const { user, loading, login, logout } = useAuth();
  return (
    <nav className="topnav">
      <div className="topnav-left">
        <Link to="/" className="topnav-brand">GitHub Pull Risk Analyzer</Link>
        <NavLink to="/" end className="topnav-link">Pull Requests</NavLink>
        <NavLink to="/evaluation" className="topnav-link">Evaluation</NavLink>
      </div>
      {!loading && (
        <div className="topnav-right">
          {user ? (
            <>
              {user.avatar_url && <img src={user.avatar_url} alt="" className="topnav-avatar" />}
              <span className="topnav-user">{user.username}</span>
              <button type="button" className="topnav-btn ghost" onClick={logout}>Sign out</button>
            </>
          ) : (
            <button type="button" className="topnav-btn" onClick={login}>Sign in with GitHub</button>
          )}
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
        <Route path="/" element={<ProtectedRoute><PRList /></ProtectedRoute>} />
        <Route path="/prs/:id" element={<ProtectedRoute><PRDetail /></ProtectedRoute>} />
        <Route path="/evaluation" element={<ProtectedRoute><Evaluation /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  );
}