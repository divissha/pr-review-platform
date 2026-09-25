import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getPRDetail, getComments, postComment } from "../api/mockApi";
import ScoreCard from "../components/ScoreCard";

export default function PRDetail() {
  const { id } = useParams();
  const [pr, setPr] = useState(null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getPRDetail(id), getComments(id)]).then(
      ([prData, commentData]) => {
        setPr(prData);
        setComments(commentData);
        setLoading(false);
      }
    );
  }, [id]);

  async function handleAddComment(e) {
    e.preventDefault();
    if (!newComment.trim()) return;
    const comment = await postComment(id, newComment);
    setComments([...comments, comment]);
    setNewComment("");
  }

  if (loading) return <div className="p-8 text-gray-500">Loading…</div>;
  if (!pr) return <div className="p-8 text-red-500">PR not found</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Link to="/" className="text-sm text-gray-500 hover:underline">
        ← Back to PR list
      </Link>
      <h1 className="text-2xl font-bold text-gray-900 mt-2 mb-1">
        {pr.title}
      </h1>
      <p className="text-sm text-gray-500 mb-6">
        {pr.repo} · #{pr.pr_number}
      </p>

      <section className="mb-6">
        <h2 className="font-semibold text-gray-800 mb-2">AI Summary</h2>
        <p className="text-gray-700 bg-gray-50 border border-gray-200 rounded-lg p-4">
          {pr.summary}
        </p>
      </section>

      <section className="mb-6">
        <h2 className="font-semibold text-gray-800 mb-2">Diff</h2>
        <pre className="bg-gray-900 text-gray-100 text-sm rounded-lg p-4 overflow-x-auto">
          {pr.diff}
        </pre>
      </section>

      <section className="mb-6">
        <h2 className="font-semibold text-gray-800 mb-3">Risk Scores</h2>
        <div className="flex flex-wrap gap-3">
          <ScoreCard
            methodName="Rule-based"
            score={pr.scores.rule_based.score}
            label={pr.scores.rule_based.label}
            reasons={pr.scores.rule_based.reasons}
          />
          <ScoreCard
            methodName="ML-based"
            score={pr.scores.ml_based.score}
            label={pr.scores.ml_based.label}
            reasons={pr.scores.ml_based.reasons}
          />
          <ScoreCard
            methodName="LLM-based"
            score={pr.scores.llm_based.score}
            label={pr.scores.llm_based.label}
            reasons={pr.scores.llm_based.reasons}
          />
        </div>
      </section>

      <section>
        <h2 className="font-semibold text-gray-800 mb-3">Comments</h2>
        <div className="space-y-3 mb-4">
          {comments.map((c) => (
            <div
              key={c.id}
              className="border border-gray-200 rounded-lg p-3 text-sm"
            >
              <span className="font-medium text-gray-800">{c.user}</span>{" "}
              <span className="text-gray-600">{c.body}</span>
            </div>
          ))}
        </div>
        <form onSubmit={handleAddComment} className="flex gap-2">
          <input
            type="text"
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Add a comment…"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <button
            type="submit"
            className="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-700"
          >
            Post
          </button>
        </form>
      </section>
    </div>
  );
}
