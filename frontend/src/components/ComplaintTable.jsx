import { useNavigate } from "react-router-dom";

import { formatDate } from "../utils/format";
import { ReportableBadge, RiskBadge, SlaBadge, StatusBadge } from "./Badges";

export default function ComplaintTable({ items, loading }) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="center-state">
        <div className="spinner dark" style={{ margin: "0 auto 12px" }} />
        Loading complaints...
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="center-state">
        No complaints yet. Use "New complaint" to log the first one.
      </div>
    );
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Reference</th>
          <th>Product</th>
          <th>Batch</th>
          <th>Type</th>
          <th>Risk</th>
          <th>Flags</th>
          <th>SLA</th>
          <th>Status</th>
          <th>Received</th>
        </tr>
      </thead>
      <tbody>
        {items.map((c) => (
          <tr key={c.id} onClick={() => navigate(`/complaints/${c.id}`)}>
            <td className="ref">{c.reference}</td>
            <td>{c.product_name || <span className="muted">Not extracted</span>}</td>
            <td>{c.batch_number || <span className="muted">-</span>}</td>
            <td>{c.complaint_type || <span className="muted">-</span>}</td>
            <td>
              <RiskBadge level={c.risk_level} />
            </td>
            <td>
              <ReportableBadge reportable={c.reportable} />
              {!c.reportable && <span className="muted">-</span>}
            </td>
            <td>
              <SlaBadge daysLeft={c.investigation_days_left} isOverdue={c.is_overdue} />
            </td>
            <td>
              <StatusBadge status={c.status} />
            </td>
            <td className="muted">{formatDate(c.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
