const STEPS = [
  { n: "01", title: "Fetch", text: "Pull a merged PR from GitHub: files, diff and metadata." },
  { n: "02", title: "Score", text: "Rate its risk three ways: rules, a trained model and an LLM." },
  { n: "03", title: "Compare", text: "Check each score against what actually happened later." },
];

const STATS = [
  { value: "1,597", label: "PRs analysed" },
  { value: "3", label: "scoring methods" },
  { value: "4", label: "open-source repos" },
  { value: "25", label: "risky PRs in the test set" },
];

const css = `
.hero { background:#0d1117; color:#f0f6fc; border:1px solid #30363d; border-radius:8px;
        padding:40px 40px 0; margin-bottom:28px; overflow:hidden; }
.hero-eyebrow { font-size:.75rem; font-weight:600; letter-spacing:.12em; text-transform:uppercase; color:#58a6ff; }
.hero-title { font-size:2.1rem; line-height:1.2; font-weight:700; letter-spacing:-.02em; margin:10px 0 12px; max-width:640px; }
.hero-sub { color:#9198a1; font-size:1rem; line-height:1.65; max-width:620px; margin:0; }
.hero-steps { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-top:32px; }
.hero-step { border-top:2px solid #30363d; padding-top:14px; }
.hero-step b { color:#58a6ff; font-size:.75rem; letter-spacing:.08em; }
.hero-step h4 { margin:4px 0 4px; font-size:1rem; font-weight:600; color:#f0f6fc; }
.hero-step p { margin:0; color:#9198a1; font-size:.85rem; line-height:1.5; }
.hero-stats { display:grid; grid-template-columns:repeat(4,1fr); margin:36px -40px 0;
              border-top:1px solid #30363d; background:#161b22; }
.hero-stat { padding:18px 40px; border-right:1px solid #30363d; }
.hero-stat:last-child { border-right:0; }
.hero-stat strong { display:block; font-size:1.6rem; font-weight:700; color:#f0f6fc; letter-spacing:-.01em; }
.hero-stat span { font-size:.75rem; color:#9198a1; text-transform:uppercase; letter-spacing:.06em; }
@media (max-width:720px) {
  .hero { padding:28px 20px 0; }
  .hero-title { font-size:1.6rem; }
  .hero-steps { grid-template-columns:1fr; }
  .hero-stats { grid-template-columns:repeat(2,1fr); margin:28px -20px 0; }
  .hero-stat { padding:14px 20px; }
  .hero-stat:nth-child(2) { border-right:0; }
  .hero-stat:nth-child(-n+2) { border-bottom:1px solid #30363d; }
}
`;

export default function Hero() {
  return (
    <section className="hero">
      <style>{css}</style>
      <div className="hero-eyebrow">Pull request risk analysis</div>
      <div className="hero-title" role="heading" aria-level={1}>
        Find the pull requests most likely to cause problems later
      </div>
      <p className="hero-sub">
        Every merged change is scored by three independent methods and checked against
        real outcomes (reverts, hotfixes and bug-fix follow-ups) from open-source
        repositories. Paste any PR URL below to analyse it live.
      </p>

      <div className="hero-steps">
        {STEPS.map((s) => (
          <div className="hero-step" key={s.n}>
            <b>{s.n}</b>
            <h4>{s.title}</h4>
            <p>{s.text}</p>
          </div>
        ))}
      </div>

      <div className="hero-stats">
        {STATS.map((s) => (
          <div className="hero-stat" key={s.label}>
            <strong>{s.value}</strong>
            <span>{s.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}