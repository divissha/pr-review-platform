import { useEffect, useState } from "react";
import { getEvaluationSummary } from "../api/api";

const NAMES = {
  rule_based: "Rule-based",
  size_only: "Size-only baseline",
  logistic_regression: "Logistic regression",
  xgboost: "XGBoost",
  llm: "LLM",
};
const ORDER = ["logistic_regression", "xgboost", "llm", "rule_based", "size_only"];
const name = (k) => NAMES[k] || k;
const ci = (m) => `[${m.lo.toFixed(3)}, ${m.hi.toFixed(3)}]`;

// Point estimate (dot), 95% interval (bar) and the chance level (vertical line).
function IntervalBar({ m, min = 0.2, max = 0.9, chance = 0.5 }) {
  const pos = (v) => Math.min(100, Math.max(0, ((v - min) / (max - min)) * 100));
  return (
    <div className="relative h-4 w-full max-w-[220px]" aria-hidden="true">
      <div className="absolute top-1/2 h-px w-full bg-line" />
      <div
        className="absolute top-1/2 -translate-y-1/2 h-1.5 rounded-full bg-accent/40"
        style={{ left: `${pos(m.lo)}%`, width: `${pos(m.hi) - pos(m.lo)}%` }}
      />
      <div
        className="absolute top-1/2 -translate-y-1/2 h-2.5 w-2.5 -ml-1 rounded-full bg-accent"
        style={{ left: `${pos(m.value)}%` }}
      />
      <div className="absolute top-0 h-full w-px bg-dim" style={{ left: `${pos(chance)}%` }} />
    </div>
  );
}

function MetricCell({ m }) {
  return (
    <div>
      <span className="font-mono text-sm text-text">{m.value.toFixed(3)}</span>{" "}
      <span className="font-mono text-xs text-dim">{ci(m)}</span>
    </div>
  );
}

export default function Evaluation() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getEvaluationSummary().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="p-8 text-high font-mono text-sm">{error}</div>;
  if (!data) return <div className="p-8 text-dim font-mono text-sm">loading…</div>;

  const keys = [
    ...ORDER.filter((k) => data.methods[k]),
    ...Object.keys(data.methods).filter((k) => !ORDER.includes(k)),
  ];

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-lg font-medium text-text mb-1">Evaluation results</h1>
      <p className="text-xs text-dim font-mono mb-1">
        {data.n_prs} eligible pull requests · {data.n_risky} labeled risky (
        {((data.n_risky / data.n_prs) * 100).toFixed(1)}%)
      </p>
      <p className="text-xs text-dim mb-6">{data.population}</p>

      <div className="border border-line rounded-md overflow-x-auto mb-3">
        <div className="min-w-[640px]">
          <div className="grid grid-cols-[1.2fr_2fr_1.3fr_1.3fr] gap-4 px-4 py-2.5 text-xs text-dim border-b border-line">
            <span>Method</span>
            <span>ROC-AUC (95% interval)</span>
            <span>PR-AUC</span>
            <span>Risky caught in top 10%</span>
          </div>
          {keys.map((k, i) => {
            const m = data.methods[k];
            return (
              <div
                key={k}
                className={`grid grid-cols-[1.2fr_2fr_1.3fr_1.3fr] gap-4 px-4 py-3 items-center ${
                  i !== keys.length - 1 ? "border-b border-line" : ""
                }`}
              >
                <span className="text-sm text-text">{name(k)}</span>
                <div className="space-y-1">
                  <MetricCell m={m.roc_auc} />
                  <IntervalBar m={m.roc_auc} />
                </div>
                <MetricCell m={m.pr_auc} />
                <MetricCell m={m.recall_top10} />
              </div>
            );
          })}
        </div>
      </div>
      <p className="text-xs text-dim mb-8">
        Vertical line = chance level (ROC-AUC 0.5). Chance for PR-AUC ≈{" "}
        {data.random_baseline.pr_auc.toFixed(3)}; chance for top-10% recall = 10%.
      </p>

      <h2 className="text-sm text-dim mb-2">Paired comparison (ROC-AUC, A minus B)</h2>
      <div className="border border-line rounded-md overflow-x-auto mb-3">
        <div className="min-w-[560px]">
          <div className="grid grid-cols-[2fr_1fr_1.4fr_1.6fr] gap-4 px-4 py-2.5 text-xs text-dim border-b border-line">
            <span>Comparison</span>
            <span>Difference</span>
            <span>95% interval</span>
            <span>Verdict</span>
          </div>
          {(data.pairs || []).map((p, i, arr) => (
            <div
              key={`${p.A}-${p.B}`}
              className={`grid grid-cols-[2fr_1fr_1.4fr_1.6fr] gap-4 px-4 py-2.5 text-sm ${
                i !== arr.length - 1 ? "border-b border-line" : ""
              }`}
            >
              <span className="text-text">
                {name(p.A)} vs {name(p.B)}
              </span>
              <span className="font-mono text-xs text-text">{Number(p.diff).toFixed(3)}</span>
              <span className="font-mono text-xs text-dim">{p["95% CI"]}</span>
              <span className={p.verdict === "no clear difference" ? "text-dim" : "text-accent"}>
                {p.verdict === "A > B"
                  ? `${name(p.A)} better`
                  : p.verdict === "B > A"
                  ? `${name(p.B)} better`
                  : p.verdict}
              </span>
            </div>
          ))}
        </div>
      </div>
      <p className="text-xs text-dim">
        With only {data.n_risky} risky PRs this study is underpowered: read these results as a
        feasibility assessment, not a ranking. Ten comparisons are shown, so about one can look
        significant by chance.
      </p>
    </div>
  );
}