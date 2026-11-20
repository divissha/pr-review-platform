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
        {(reasons || []).map((r, i) => (
          <li key={i}>{r}</li>
        ))}
      </ul>
    </div>
  );
}




// import RiskBadge from "./RiskBadge";

// const riskColor = {
//   low: "text-low",
//   medium: "text-medium",
//   high: "text-high",
// };

// export default function ScoreCard({ methodName, score, label, reasons }) {
//   return (
//     <div className="border border-line bg-panel rounded-md p-5 flex-1 min-w-[240px]">
//       <div className="flex items-start justify-between mb-4">
//         <span className="text-sm text-dim">{methodName}</span>
//         <RiskBadge level={label} />
//       </div>
//       <div className={`font-mono text-4xl font-medium mb-4 ${riskColor[label] || "text-text"}`}>
//         {score}
//       </div>
//       <ul className="space-y-1.5">
//         {reasons.map((r, i) => (
//           <li key={i} className="text-sm text-dim flex gap-2">
//             <span className="text-dim/60 select-none">–</span>
//             <span>{r}</span>
//           </li>
//         ))}
//       </ul>
//     </div>
//   );
// }