import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getPRs } from "../api/mockApi";
import RiskBadge from "../components/RiskBadge";

export default function PRList() {
  const [prs, setPrs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPRs().then((data) => {
      setPrs(data);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="p-8 text-gray-500">Loading pull requests…</div>;
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Pull Requests</h1>
      <div className="space-y-3">
        {prs.map((pr) => (
          <Link
            to={`/prs/${pr.id}`}
            key={pr.id}
            className="block border border-gray-200 rounded-lg p-4 hover:border-gray-400 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">{pr.title}</p>
                <p className="text-sm text-gray-500">
                  {pr.repo} · #{pr.pr_number} · {pr.status}
                </p>
              </div>
              <RiskBadge level={pr.overall_risk} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
