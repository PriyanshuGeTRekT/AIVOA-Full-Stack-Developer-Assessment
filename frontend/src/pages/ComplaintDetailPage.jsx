import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useParams } from "react-router-dom";

import { RiskBadge } from "../components/Badges";
import { formatDate } from "../utils/format";
import {
  changeStatus,
  fetchComplaint,
  fetchStats,
  reprocessComplaint,
} from "../store/complaintsSlice";

export default function ComplaintDetailPage() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const complaint = useSelector((s) => s.complaints.selected);
  const [reprocessing, setReprocessing] = useState(false);

  useEffect(() => {
    dispatch(fetchComplaint(Number(id)));
  }, [dispatch, id]);

  if (!complaint || complaint.id !== Number(id)) {
    return (
      <div className="main">
        <div className="center-state">
          <div className="spinner dark" style={{ margin: "0 auto 12px" }} />
          Loading complaint...
        </div>
      </div>
    );
  }

  async function onStatusChange(e) {
    await dispatch(changeStatus({ id: complaint.id, status: e.target.value }));
    dispatch(fetchStats());
  }

  async function onReprocess() {
    setReprocessing(true);
    await dispatch(reprocessComplaint(complaint.id));
    dispatch(fetchStats());
    setReprocessing(false);
  }

  const completeness = complaint.completeness;

  return (
    <div className="main">
      <Link to="/" className="back-link">
        ← Back to complaints
      </Link>

      <div className="page-head">
        <div>
          <h1 className="page-title">{complaint.reference}</h1>
          <p className="page-subtitle">
            {complaint.channel} intake · received {formatDate(complaint.created_at)}
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <select
            className="status-select"
            value={complaint.status}
            onChange={onStatusChange}
          >
            <option value="open">Open</option>
            <option value="under_review">Under review</option>
            <option value="closed">Closed</option>
          </select>
          <button className="btn btn-ghost" onClick={onReprocess} disabled={reprocessing}>
            {reprocessing ? (
              <>
                <span className="spinner dark" /> Re-running...
              </>
            ) : (
              "Re-run AI"
            )}
          </button>
        </div>
      </div>

      {/* Duplicate warning surfaces prominently since it changes how the QA
          reviewer handles the record. */}
      {complaint.duplicate_of && (
        <div className="alert warn">
          <span>⚠️</span>
          <div>
            This looks like a possible duplicate of complaint #{complaint.duplicate_of}
            {complaint.duplicate_score
              ? ` (similarity ${Math.round(complaint.duplicate_score * 100)}%)`
              : ""}
            . Review before opening a new investigation.
          </div>
        </div>
      )}

      {completeness && !completeness.is_complete && (
        <div className="alert danger">
          <span>📌</span>
          <div>
            Incomplete record. Missing: {completeness.missing_fields.join(", ") || "details"}.
            {completeness.notes ? ` ${completeness.notes}` : ""}
          </div>
        </div>
      )}
      {completeness && completeness.is_complete && (
        <div className="alert ok">
          <span>✓</span>
          <div>Record is complete and ready for investigation.</div>
        </div>
      )}

      <div className="detail-grid">
        <div className="card" style={{ padding: 22 }}>
          <div className="ai-block">
            <h4>
              Extracted details <span className="ai-tag">AI extraction</span>
            </h4>
            <Field label="Product" value={complaint.product_name} />
            <Field label="Batch / Lot" value={complaint.batch_number} />
            <Field label="Complaint type" value={complaint.complaint_type} />
            <Field label="Complainant" value={complaint.complainant_name} />
            <Field label="Contact" value={complaint.complainant_contact} />
            <Field label="Description" value={complaint.description} />
          </div>

          <div className="ai-block">
            <h4>
              Risk classification <span className="ai-tag">AI triage</span>
            </h4>
            <div style={{ marginBottom: 8 }}>
              <RiskBadge level={complaint.risk_level} />
            </div>
            <p className="ai-text">{complaint.risk_rationale || "No rationale available."}</p>
          </div>

          <div className="ai-block">
            <h4>
              Summary <span className="ai-tag">AI summary</span>
            </h4>
            <p className="ai-text">{complaint.summary || "-"}</p>
          </div>

          <div className="ai-block">
            <h4>
              Probable root cause <span className="ai-tag">AI suggestion</span>
            </h4>
            <p className="ai-text">{complaint.root_cause || "-"}</p>
          </div>

          <div className="ai-block">
            <h4>
              Recommended CAPA <span className="ai-tag">AI suggestion</span>
            </h4>
            <p className="ai-text">{complaint.capa || "-"}</p>
          </div>
        </div>

        <div className="card" style={{ padding: 22 }}>
          <h3 className="section-title">Original complaint</h3>
          <div className="source-box">{complaint.source_text}</div>
          {complaint.original_filename && (
            <p className="muted" style={{ marginTop: 10 }}>
              Source file: {complaint.original_filename}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, value }) {
  return (
    <div className="field-row">
      <span className="field-label">{label}</span>
      <span className="field-value">
        {value || <span className="muted">Not found</span>}
      </span>
    </div>
  );
}
