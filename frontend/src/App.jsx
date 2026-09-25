import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import PRList from "./pages/PRList";
import PRDetail from "./pages/PRDetail";
import Evaluation from "./pages/Evaluation";

function Nav() {
  return (
    <nav className="border-b border-gray-200 px-6 py-3 flex gap-6">
      <Link to="/" className="font-semibold text-gray-900">
        PR Review Platform
      </Link>
      <Link to="/" className="text-gray-600 hover:text-gray-900">
        Pull Requests
      </Link>
      <Link to="/evaluation" className="text-gray-600 hover:text-gray-900">
        Evaluation
      </Link>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <Routes>
        <Route path="/" element={<PRList />} />
        <Route path="/prs/:id" element={<PRDetail />} />
        <Route path="/evaluation" element={<Evaluation />} />
      </Routes>
    </BrowserRouter>
  );
}
