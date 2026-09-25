import RiskBadge from "./RiskBadge";

export default function ScoreCard({ methodName, score, label, reasons }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 flex-1 min-w-[220px]">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-gray-800">{methodName}</h3>
        <RiskBadge level={label} />
      </div>
      <div className="text-3xl font-bold text-gray-900 mb-2">{score}</div>
      <ul className="text-sm text-gray-600 list-disc list-inside space-y-0.5">
        {reasons.map((r, i) => (
          <li key={i}>{r}</li>
        ))}
      </ul>
    </div>
  );
}
