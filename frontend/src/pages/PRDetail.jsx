import { useEffect, useState } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import { getPRDetail, getComments, postComment } from "../api/api";
import ScoreCard from "../components/ScoreCard";
import StaticAnalysis from "../components/StaticAnalysis";

const METHODS = [
  { key: "rule_based", name: "Rule-based" },
  { key: "ml_based", name: "ML-based" },
  { key: "llm_based", name: "LLM-based" },
];

function DiffLine({ line }) {
  let cls = "text-dim";
  if (line.startsWith("+") && !line.startsWith("+++")) cls = "text-low bg-low/10";
  else if (line.startsWith("-") && !line.startsWith("---")) cls = "text-high bg-high/10";
  else if (line.startsWith("@@")) cls = "text-accent";
  return <div className={`px-3 ${cls}`}>{line || " "}</div>;
}

export default function PRDetail() {
  const { id } = useParams();
  const location = useLocation();
  const warnings = location.state?.warnings || [];
  const [pr, setPr] = useState(null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([getPRDetail(id), getComments(id)])
      .then(([prData, commentData]) => {
        setPr(prData);
        setComments(commentData);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleAddComment(e) {
    e.preventDefault();
    if (!newComment.trim()) return;
    try {
      const comment = await postComment(id, newComment);
      setComments((prev) => [...prev, comment]);
      setNewComment("");
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <div className="p-8 text-dim font-mono text-sm">loading…</div>;
  if (error && !pr) {
    return <div className="p-8 text-high font-mono text-sm">Could not load this PR: {error}</div>;
  }
  if (!pr) return <div className="p-8 text-high font-mono text-sm">PR not found</div>;

  const scores = pr.scores || {};
  const hasOutcome = pr.actual_outcome !== null && pr.actual_outcome !== undefined;

  return (
    <div className="max-w-3xl mx-auto p-6">
      <Link to="/" className="text-xs text-dim hover:text-accent font-mono">
        ← back
      </Link>
      <h1 className="text-xl font-medium text-text mt-2 mb-1">{pr.title}</h1>
            <p className="text-xs text-dim font-mono mb-8">
        {pr.repo} · #{pr.pr_number}
        {pr.source === "live" && (
          <span className="ml-2 text-accent border border-accent/40 rounded px-1.5 py-0.5">
            live analysis
          </span>
        )}
      </p>

      {warnings.length > 0 && (
        <div className="mb-8 border border-medium/40 bg-medium/10 rounded-md px-4 py-3">
          <p className="text-sm text-medium mb-1">Some parts of this analysis are incomplete</p>
          <ul className="text-xs text-dim space-y-1">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <section className="mb-8">
        <h2 className="text-sm text-dim mb-2">Summary</h2>
        <p className="text-sm text-text leading-relaxed border-l-2 border-accent/40 pl-4">
          {pr.summary || "No summary available."}
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-sm text-dim mb-2">Diff</h2>
        <div className="bg-panel border border-line rounded-md py-3 font-mono text-xs overflow-x-auto max-h-[28rem] overflow-y-auto">
          {pr.diff
            ? pr.diff.split("\n").map((line, i) => <DiffLine key={i} line={line} />)
            : <div className="px-3 text-dim">(diff not available)</div>}
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-sm text-dim mb-1">Risk scores</h2>
        <p className="text-xs text-dim mb-3">
          Rule-based and LLM scores are 0–100 risk ratings. The ML score is a percentile rank
          among all reviewed PRs.
        </p>
        <div className="flex flex-wrap gap-3">
          {METHODS.map(({ key, name }) => {
            const s = scores[key];
            if (!s) {
              return (
                <div key={key} className="border border-line bg-panel rounded-md p-5 flex-1 min-w-[240px]">
                  <span className="text-sm text-dim">{name}</span>
                  <p className="text-sm text-dim mt-4">Not scored for this PR.</p>
                </div>
              );
            }
            return (
              <ScoreCard key={key} methodName={name} score={s.score} label={s.label} reasons={s.reasons} />
            );
          })}
        </div>
      </section>

      {pr.static_analysis && <StaticAnalysis data={pr.static_analysis} />}

      {hasOutcome && (
        <section className="mb-8">
          <h2 className="text-sm text-dim mb-2">What happened afterwards (proxy label)</h2>
          <p className="text-sm text-text border border-line rounded-md px-4 py-3">
            {pr.actual_outcome
              ? "A later change reverted this PR, hot-fixed the same files, or cited it as the source of a bug."
              : "No follow-up problem was detected within the observation window."}
          </p>
        </section>
      )}

      <section>
        <h2 className="text-sm text-dim mb-3">Comments</h2>
        {error && <p className="text-high text-xs font-mono mb-2">{error}</p>}
        <div className="space-y-2 mb-3">
          {comments.map((c) => (
            <div key={c.id} className="border border-line rounded-md px-3 py-2 text-sm">
              <span className="text-accent font-mono text-xs">{c.user}</span>{" "}
              <span className="text-text">{c.body}</span>
            </div>
          ))}
        </div>
        <form onSubmit={handleAddComment} className="flex gap-2">
          <input
            type="text"
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Add a comment…"
            className="flex-1 bg-panel border border-line rounded-md px-3 py-2 text-sm text-text placeholder:text-dim focus:outline-none focus:border-accent"
          />
          <button
            type="submit"
            className="bg-accent text-ink px-4 py-2 rounded-md text-sm font-medium hover:opacity-90"
          >
            Post
          </button>
        </form>
      </section>
    </div>
  );
}