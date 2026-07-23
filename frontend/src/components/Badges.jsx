import { riskClass } from "../utils/format";

// Two tiny presentational badges kept together because they share the pattern.

export function RiskBadge({ level }) {
  if (!level) return <span className="badge neutral">Unrated</span>;
  return <span className={`badge ${riskClass(level)}`}>{level}</span>;
}

const STATUS_LABELS = {
  open: "Open",
  under_review: "Under review",
  closed: "Closed",
};

export function StatusBadge({ status }) {
  return (
    <span className={`badge status-badge ${status}`}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}
