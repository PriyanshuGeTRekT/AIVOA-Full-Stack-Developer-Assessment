import { riskClass } from "../utils/format";

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

export function SlaBadge({ daysLeft, isOverdue }) {
  if (daysLeft === null || daysLeft === undefined) {
    return <span className="muted">-</span>;
  }
  if (isOverdue) {
    return <span className="badge critical">Overdue {Math.abs(daysLeft)}d</span>;
  }
  if (daysLeft <= 3) {
    return <span className="badge major">Due in {daysLeft}d</span>;
  }
  return <span className="badge minor">{daysLeft}d left</span>;
}

export function ReportableBadge({ reportable }) {
  if (!reportable) return null;
  return <span className="badge critical">Reportable</span>;
}
