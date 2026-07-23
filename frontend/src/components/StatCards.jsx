import { useSelector } from "react-redux";

// Top of dashboard summary tiles, driven straight from the stats slice.
export default function StatCards() {
  const stats = useSelector((s) => s.complaints.stats);

  const cards = [
    { label: "Total complaints", value: stats.total, tone: "" },
    { label: "Open", value: stats.open, tone: "" },
    { label: "Critical risk", value: stats.critical, tone: "critical" },
    { label: "Under review", value: stats.under_review, tone: "major" },
  ];

  return (
    <div className="stat-grid">
      {cards.map((card) => (
        <div className="stat-card" key={card.label}>
          <div className="stat-label">{card.label}</div>
          <div className={`stat-value ${card.tone}`}>{card.value}</div>
        </div>
      ))}
    </div>
  );
}
