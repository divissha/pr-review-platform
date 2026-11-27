import { useEffect, useState } from "react";
import { getEvaluationSummary } from "../api/api";

const NAMES = {
  rule_based: "Rule-based",
  size_only: "Size-only baseline",
  logistic_regression: "Logistic regression",
  xgboost: "XGBoost",
  llm: "LLM (Claude Haiku)",
};
const ORDER = ["logistic_regression", "xgboost", "llm", "rule_based", "size_only"];
const name = (k) => NAMES[k] || k;
const f3 = (v) => Number(v).toFixed(3);

const css = `
.ev { color:#1f2328; }
.ev-sub { color:#656d76; font-size:.9rem; margin:8px 0 24px; max-width:820px; line-height:1.55; }
.ev-kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:28px; }
.ev-kpi { background:#fff; border:1px solid #d0d7de; border-radius:8px; padding:16px 18px; }
.ev-kpi small { display:block; font-size:.7rem; font-weight:600; letter-spacing:.07em; text-transform:uppercase; color:#656d76; }
.ev-kpi strong { display:block; font-size:1.7rem; font-weight:700; letter-spacing:-.02em; margin-top:4px; }
.ev-kpi span { font-size:.78rem; color:#656d76; }
.ev-callout { background:#fff; border:1px solid #d0d7de; border-left:4px solid #0969da; border-radius:8px;
              padding:14px 18px; margin-bottom:28px; font-size:.92rem; line-height:1.6; }
.ev-section { margin:0 0 10px; }
.ev-card { background:#fff; border:1px solid #d0d7de; border-radius:8px; overflow-x:auto; margin-bottom:10px; }
.ev-table { width:100%; min-width:760px; border-collapse:separate; border-spacing:0; }
.ev-table th { background:#f6f8fa; color:#656d76; font-size:.7rem; font-weight:600; text-transform:uppercase;
               letter-spacing:.07em; text-align:left; padding:11px 18px; border-bottom:1px solid #d0d7de; }
.ev-table td { padding:14px 18px; border-bottom:1px solid #eaeef2; vertical-align:middle; font-size:.9rem; }
.ev-table tr:last-child td { border-bottom:0; }
.ev-table tbody tr:hover td { background:#f6f8fa; }
.ev-name { font-weight:600; }
.ev-mono { font-family:"JetBrains Mono",ui-monospace,Menlo,monospace; font-size:.82rem; }
.ev-ci { color:#656d76; margin-left:6px; font-size:.75rem; }
.ev-bar { position:relative; height:18px; width:100%; max-width:260px; margin-top:8px; }
.ev-bar .axis { position:absolute; top:50%; left:0; right:0; height:1px; background:#d0d7de; }
.ev-bar .range { position:absolute; top:50%; height:6px; margin-top:-3px; border-radius:3px; background:#b6d4fe; }
.ev-bar .dot { position:absolute; top:50%; width:10px; height:10px; margin:-5px 0 0 -5px; border-radius:50%; background:#0969da; }
.ev-bar .chance { position:absolute; top:0; bottom:0; width:2px; background:#1f2328; opacity:.55; }
.ev-bar-scale { display:flex; justify-content:space-between; max-width:260px; font-size:.65rem; color:#8c959f; margin-top:2px; }
.ev-pill { display:inline-block; padding:2px 10px; border-radius:999px; font-size:.7rem; font-weight:600;
           letter-spacing:.05em; text-transform:uppercase; border:1px solid; white-space:nowrap; }
.ev-pill.above { background:#dafbe1; color:#116329; border-color:#1a7f37; }
.ev-pill.chance { background:#f6f8fa; color:#424a53; border-color:#8c959f; }
.ev-note { font-size:.8rem; color:#656d76; line-height:1.55; margin-bottom:28px; }
.ev-warn { background:#fff8c5; border:1px solid #d4a72c; border-radius:8px; padding:14px 18px; font-size:.88rem; line-height:1.6; color:#4d3800; }
.ev-better { color:#0969da; font-weight:600; }
@media (max-width:900px) { .ev-kpis { grid-template-columns:repeat(2,1fr); } }
`;

// Point estimate (dot), 95% interval (bar) and chance level (vertical line).
function IntervalBar({ m, min = 0.2, max = 0.95, chance = 0.5 }) {
  const pos = (v) => Math.min(100, Math.max(0, ((v - min) / (max - min)) * 100));
  return (
    <div>
      <div className="ev-bar" aria-hidden="true">
        <div className="axis" />
        <div className="range" style={{ left: `${pos(m.lo)}%`, width: `${pos(m.hi) - pos(m.lo)}%` }} />
        <div className="chance" style={{ left: `${pos(chance)}%` }} />
        <div className="dot" style={{ left: `${pos(m.value)}%` }} />
      </div>
      <div className="ev-bar-scale"><span>{min}</span><span>chance 0.5</span><span>{max}</span></div>
    </div>
  );
}

function Metric({ m }) {
  return (
    <span className="ev-mono">
      {f3(m.value)}
      <span className="ev-ci">[{f3(m.lo)}, {f3(m.hi)}]</span>
    </span>
  );
}

export default function Evaluation() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getEvaluationSummary().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="p-8" style={{ color: "#cf222e" }}>{error}</div>;
  if (!data) return <div className="p-8" style={{ color: "#656d76" }}>Loading…</div>;

  const keys = [
    ...ORDER.filter((k) => data.methods[k]),
    ...Object.keys(data.methods).filter((k) => !ORDER.includes(k)),
  ];
  const best = keys.reduce((a, b) => (data.methods[b].roc_auc.value > data.methods[a].roc_auc.value ? b : a), keys[0]);
  const bestM = data.methods[best].roc_auc;
  const aboveChance = keys.filter((k) => data.methods[k].roc_auc.lo > 0.5);
  const riskyPct = ((data.n_risky / data.n_prs) * 100).toFixed(1);

  return (
    <div className="ev max-w-4xl mx-auto p-6">
      <style>{css}</style>
      <h1>Evaluation results</h1>
      <p className="ev-sub">
        How well each method ranks pull requests that later turned out to be risky (reverted,
        hot-fixed or linked to a bug fix). {data.population}
      </p>

      <div className="ev-kpis">
        <div className="ev-kpi"><small>Eligible PRs</small><strong>{data.n_prs}</strong><span>change source code</span></div>
        <div className="ev-kpi"><small>Labelled risky</small><strong>{data.n_risky}</strong><span>{riskyPct}% of the set</span></div>
        <div className="ev-kpi"><small>Methods compared</small><strong>{keys.length}</strong><span>3 main + 2 baselines</span></div>
        <div className="ev-kpi"><small>Best ROC-AUC</small><strong>{f3(bestM.value)}</strong><span>{name(best)}</span></div>
      </div>

      <div className="ev-callout">
        <b>Key finding.</b>{" "}
        {aboveChance.length
          ? `Only ${aboveChance.map(name).join(", ")} ranked risky PRs better than chance, meaning its 95% interval stays above 0.5. `
          : "No method ranked risky PRs clearly better than chance. "}
        The other methods cannot be told apart from random guessing on this data.
      </div>

      <h2 className="ev-section">Ranking quality by method</h2>
      <div className="ev-card">
        <table className="ev-table">
          <thead>
            <tr>
              <th>Method</th>
              <th>ROC-AUC (95% interval)</th>
              <th>PR-AUC</th>
              <th>Risky caught in top 10%</th>
              <th>Versus chance</th>
            </tr>
          </thead>
          <tbody>
            {keys.map((k) => {
              const m = data.methods[k];
              const above = m.roc_auc.lo > 0.5;
              return (
                <tr key={k}>
                  <td className="ev-name">{name(k)}</td>
                  <td><Metric m={m.roc_auc} /><IntervalBar m={m.roc_auc} /></td>
                  <td><Metric m={m.pr_auc} /></td>
                  <td><Metric m={m.recall_top10} /></td>
                  <td>
                    <span className={`ev-pill ${above ? "above" : "chance"}`}>
                      {above ? "Above chance" : "Within chance"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="ev-note">
        Dark vertical line = chance level (ROC-AUC 0.5). Chance for PR-AUC ≈{" "}
        {f3(data.random_baseline.pr_auc)}; chance for top-10% recall = 10%.
      </p>

      <h2 className="ev-section">Paired comparison (ROC-AUC, A minus B)</h2>
      <div className="ev-card">
        <table className="ev-table" style={{ minWidth: 640 }}>
          <thead>
            <tr><th>Comparison</th><th>Difference</th><th>95% interval</th><th>Verdict</th></tr>
          </thead>
          <tbody>
            {(data.pairs || []).map((p) => (
              <tr key={`${p.A}-${p.B}`}>
                <td className="ev-name">{name(p.A)} vs {name(p.B)}</td>
                <td className="ev-mono">{f3(p.diff)}</td>
                <td className="ev-mono" style={{ color: "#656d76" }}>{p["95% CI"]}</td>
                <td>
                  {p.verdict === "A > B" ? <span className="ev-better">{name(p.A)} better</span>
                    : p.verdict === "B > A" ? <span className="ev-better">{name(p.B)} better</span>
                    : <span style={{ color: "#656d76" }}>{p.verdict}</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="ev-note">Ten comparisons are shown, so about one can look significant by chance.</p>

      <div className="ev-warn">
        <b>Limitations.</b> With only {data.n_risky} risky PRs this study is underpowered, so read these
        results as a feasibility assessment, not a ranking. Risk labels are proxies (reverts, quick
        hotfixes, bug references) and are noisy.
      </div>
    </div>
  );
}