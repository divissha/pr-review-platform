import { useEffect, useState } from "react";
import { getEvaluationSummary } from "../api/mockApi";

const methodLabels = {
  rule_based: "Rule-based",
  ml_based: "ML-based",
  llm_based: "LLM-based",
};

export default function Evaluation() {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    getEvaluationSummary().then(setSummary);
  }, []);

  if (!summary) return <div className="p-8 text-gray-500">Loading…</div>;

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">
        Evaluation Results
      </h1>
      <p className="text-sm text-gray-500 mb-6">
        Based on {summary.dataset_size} historical pull requests
      </p>

      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-gray-300 text-left text-gray-500">
            <th className="py-2">Method</th>
            <th className="py-2">Precision</th>
            <th className="py-2">Recall</th>
            <th className="py-2">F1</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(summary.metrics).map(([key, m]) => (
            <tr key={key} className="border-b border-gray-100">
              <td className="py-2 font-medium text-gray-800">
                {methodLabels[key] || key}
              </td>
              <td className="py-2">{m.precision.toFixed(2)}</td>
              <td className="py-2">{m.recall.toFixed(2)}</td>
              <td className="py-2">{m.f1.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
