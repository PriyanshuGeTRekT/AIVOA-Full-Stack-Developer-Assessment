import { useSelector } from "react-redux";

// Dashboard counters; click a card to filter the worklist.
export default function StatCards({ onFilter }) {
  const stats = useSelector((s) => s.complaints.stats);

  const cards = [
    {
      label: "Total complaints",
      value: stats.total,
      tone: "",
      filter: { status: "", risk_level: "", reportable: "", overdue: "", q: "" },
    },
    {
      label: "Open",
      value: stats.open,
      tone: "",
      filter: { status: "open", risk_level: "", reportable: "", overdue: "" },
    },
    {
      label: "Critical risk",
      value: stats.critical,
      tone: "critical",
      filter: { risk_level: "Critical", status: "", reportable: "", overdue: "" },
    },
    {
      label: "Reportable",
      value: stats.reportable,
      tone: "major",
      hint: "Regulatory report due",
      filter: { reportable: "true", status: "", risk_level: "", overdue: "" },
    },
    {
      label: "Overdue",
      value: stats.overdue,
      tone: stats.overdue ? "critical" : "",
      hint: "Past investigation SLA",
      filter: { overdue: "true", status: "", risk_level: "", reportable: "" },
    },
  ];

  return (
    <div className="stat-grid">
      {cards.map((card) => (
        <button
          type="button"
          className="stat-card stat-card-btn"
          key={card.label}
          onClick={() => onFilter?.({ ...card.filter, page: 1 })}
          title={`Filter worklist: ${card.label}`}
        >
          <div className="stat-label">{card.label}</div>
          <div className={`stat-value ${card.tone}`}>{card.value}</div>
          {card.hint && <div className="stat-hint">{card.hint}</div>}
        </button>
      ))}
    </div>
  );
}
