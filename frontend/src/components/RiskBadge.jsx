const config = {
  low: { color: "text-low", border: "border-low/40", bg: "bg-low/10", glyph: "▬" },
  medium: { color: "text-medium", border: "border-medium/40", bg: "bg-medium/10", glyph: "▲" },
  high: { color: "text-high", border: "border-high/40", bg: "bg-high/10", glyph: "▲▲" },
};

export default function RiskBadge({ level }) {
  if (!level) {
    return <span className="font-mono text-xs text-dim">unscored</span>;
  }
  const c = config[level] || config.medium;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border font-mono text-xs ${c.color} ${c.border} ${c.bg}`}
    >
      <span aria-hidden="true">{c.glyph}</span>
      {level}
    </span>
  );
}