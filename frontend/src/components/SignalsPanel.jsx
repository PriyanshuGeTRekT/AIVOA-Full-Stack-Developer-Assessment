import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";

// Batch / product-defect clusters from the signals API.
export default function SignalsPanel() {
  const signals = useSelector((s) => s.complaints.signals);
  const navigate = useNavigate();

  if (!signals.length) return null;

  return (
    <div className="signals-panel">
      <h3>⚡ Quality signals detected</h3>
      <p className="sub">
        Multiple complaints appear to share a root problem. Review these clusters
        before treating the individual complaints in isolation.
      </p>
      {signals.map((signal, i) => (
        <div className="signal-row" key={`${signal.kind}-${i}`}>
          <div className="signal-main">
            <span className="signal-title">
              {signal.label}
              {signal.severity ? ` · ${signal.severity} severity` : ""}
            </span>
            <span className="signal-rec">{signal.recommendation}</span>
            <span className="signal-rec">
              Related:{" "}
              {signal.complaint_ids.map((id, idx) => (
                <span key={id}>
                  <span
                    className="ref"
                    style={{ cursor: "pointer" }}
                    onClick={() => navigate(`/complaints/${id}`)}
                  >
                    {signal.references[idx]}
                  </span>
                  {idx < signal.complaint_ids.length - 1 ? ", " : ""}
                </span>
              ))}
            </span>
          </div>
          <div className="signal-count">{signal.count} complaints</div>
        </div>
      ))}
    </div>
  );
}
