const styles = {
  low: "bg-green-100 text-green-700 border-green-300",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-300",
  high: "bg-red-100 text-red-700 border-red-300",
};

export default function RiskBadge({ level }) {
  const cls = styles[level] || styles.medium;
  return (
    <span
      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium border ${cls}`}
    >
      {level}
    </span>
  );
}
