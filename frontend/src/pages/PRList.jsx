import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getPRs, analyzePR } from "../api/api";
import RiskBadge from "../components/RiskBadge";

export default function PRList() {
  const navigate = useNavigate();
  const [prs, setPrs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");

  const [url, setUrl] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState(null);

  useEffect(() => {
    getPRs()
      .then(setPrs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleAnalyze(e) {
    e.preventDefault();
    if (!url.trim() || analyzing) return;
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      const pr = await analyzePR(url.trim());
      navigate(`/prs/${pr.id}`, { state: { warnings: pr.warnings || [] } });
    } catch (err) {
      setAnalyzeError(err.message);
    } finally {
      setAnalyzing(false);
    }
  }

  if (loading) {
    return <div className="p-8 text-dim font-mono text-sm">loading pull requests…</div>;
  }
  if (error) {
    return (
      <div className="p-8 text-high font-mono text-sm">
        Could not load pull requests: {error}. Is the Django server running?
      </div>
    );
  }

  const q = query.trim().toLowerCase();
  const shown = q
    ? prs.filter((pr) => pr.title.toLowerCase().includes(q) || pr.repo.toLowerCase().includes(q))
    : prs;

  return (
    <div className="max-w-3xl mx-auto p-6">
      <form onSubmit={handleAnalyze} className="mb-8">
        <label htmlFor="pr-url" className="block text-sm text-dim mb-2">
          Analyze any GitHub pull request
        </label>
        <div className="flex gap-2">
          <input
            id="pr-url"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={analyzing}
            placeholder="https://github.com/owner/repo/pull/123"
            className="flex-1 bg-panel border border-line rounded-md px-3 py-2 text-sm text-text placeholder:text-dim focus:outline-none focus:border-accent disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={analyzing}
            className="bg-accent text-ink px-4 py-2 rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50"
          >
            {analyzing ? "Analyzing…" : "Analyze"}
          </button>
        </div>
        {analyzing && (
          <p className="text-xs text-dim mt-2">
            Fetching the PR and scoring it with all three methods. This usually takes 10–40 seconds.
          </p>
        )}
        {analyzeError && <p className="text-xs text-high font-mono mt-2">{analyzeError}</p>}
      </form>

      <div className="flex items-baseline justify-between mb-4">
        <h1 className="text-lg font-medium text-text">Pull requests</h1>
        <span className="text-xs text-dim font-mono">
          {shown.length} of {prs.length}
        </span>
      </div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Filter by title or repository…"
        className="w-full mb-4 bg-panel border border-line rounded-md px-3 py-2 text-sm text-text placeholder:text-dim focus:outline-none focus:border-accent"
      />
      <div className="border border-line rounded-md overflow-hidden">
        {shown.length === 0 && <div className="p-4 text-sm text-dim">No pull requests match.</div>}
        {shown.map((pr, i) => (
          <Link
            to={`/prs/${pr.id}`}
            key={pr.id}
            className={`flex items-center gap-4 px-4 py-3 hover:bg-panel2 transition-colors ${
              i !== shown.length - 1 ? "border-b border-line" : ""
            }`}
          >
            <span className="font-mono text-xs text-dim w-14 shrink-0">#{pr.pr_number}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-text truncate">{pr.title}</p>
              <p className="text-xs text-dim font-mono mt-0.5">
                {pr.repo} · {pr.status}
                {pr.source === "live" && (
                  <span className="ml-2 text-accent border border-accent/40 rounded px-1.5 py-0.5">live</span>
                )}
              </p>
            </div>
            <RiskBadge level={pr.overall_risk} />
          </Link>
        ))}
      </div>
    </div>
  );
}