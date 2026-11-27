const COLORS = {
  low: { bg: "#dafbe1", border: "#1a7f37", fg: "#116329" },
  medium: { bg: "#fff8c5", border: "#bf8700", fg: "#7d4e00" },
  high: { bg: "#ffebe9", border: "#cf222e", fg: "#a40e26" },
};

export default function RiskBadge({ level }) {
  const key = String(level || "").toLowerCase();
  const c = COLORS[key] || { bg: "#f6f8fa", border: "#656d76", fg: "#424a53" };
  return (
    <span
      data-risk={key}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "2px 11px",
        borderRadius: 999,
        fontSize: "0.72rem",
        fontWeight: 600,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        background: c.bg,
        color: c.fg,
        border: `1px solid ${c.border}`,
        whiteSpace: "nowrap",
      }}
    >
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: "50%",
          background: c.border,
          display: "inline-block",
        }}
      />
      {key || "n/a"}
    </span>
  );
}