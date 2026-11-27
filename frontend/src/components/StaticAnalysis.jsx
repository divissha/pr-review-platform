const SEVERITY_STYLE = {
  high: "text-high border-high/40 bg-high/10",
  medium: "text-medium border-medium/40 bg-medium/10",
  low: "text-dim border-line bg-panel2",
};

export default function StaticAnalysis({ data }) {
  const findings = data.findings || [];
  const onChanged = findings.filter((f) => f.on_changed_line);
  const elsewhere = findings.length - onChanged.length;

  return (
    <section className="mb-8">
      <h2 className="text-sm text-dim mb-1">Static analysis (Bandit)</h2>
      <p className="text-xs text-dim mb-3">
        Extra evidence from a Python security linter. It is not part of any risk score.
      </p>

      {data.note && <p className="text-xs text-dim mb-3">{data.note}</p>}

      {data.files_scanned > 0 && (
        <p className="text-xs text-dim font-mono mb-3">
          {data.files_scanned} Python file{data.files_scanned === 1 ? "" : "s"} scanned ·{" "}
          {onChanged.length} finding{onChanged.length === 1 ? "" : "s"} on lines this PR changed ·{" "}
          {elsewhere} elsewhere in the same files
        </p>
      )}

      {data.files_scanned > 0 && onChanged.length === 0 && (
        <p className="text-sm text-text border border-line rounded-md px-4 py-3">
          No Bandit findings on the changed lines. That does not mean the change is safe: Bandit
          only checks for a fixed set of Python security patterns.
        </p>
      )}

      {onChanged.length > 0 && (
        <ul className="border border-line rounded-md divide-y divide-line">
          {onChanged.map((f, i) => (
            <li key={`${f.file}-${f.line}-${f.rule_id}-${i}`} className="px-4 py-3">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={`font-mono text-xs px-2 py-0.5 rounded border ${
                    SEVERITY_STYLE[f.severity] || SEVERITY_STYLE.low
                  }`}
                >
                  {f.severity}
                </span>
                <span className="font-mono text-xs text-dim">
                  {f.file}:{f.line}
                </span>
                <span className="font-mono text-xs text-dim ml-auto">{f.rule_id}</span>
              </div>
              <p className="text-sm text-text">{f.message}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}