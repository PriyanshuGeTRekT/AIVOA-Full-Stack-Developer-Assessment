import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate, useParams } from "react-router-dom";

import { complaintsApi } from "../api/client";
import { RiskBadge, SlaBadge } from "../components/Badges";
import { formatDate } from "../utils/format";
import {
  changeStatus,
  fetchComplaint,
  fetchSignals,
  fetchStats,
  overrideRisk,
  reprocessComplaint,
} from "../store/complaintsSlice";

export default function ComplaintDetailPage() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const complaint = useSelector((s) => s.complaints.selected);
  const [reprocessing, setReprocessing] = useState(false);
  const [related, setRelated] = useState(null);

  useEffect(() => {
    dispatch(fetchComplaint(Number(id)));
    complaintsApi.related(Number(id)).then(setRelated).catch(() => setRelated(null));
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
    const next = e.target.value;
    const result = await dispatch(changeStatus({ id: complaint.id, status: next }));
    if (result.meta.requestStatus === "fulfilled") {
      dispatch(fetchStats());
    } else {
      e.target.value = complaint.status;
      window.alert(result.payload || "That status change is not allowed.");
    }
  }

  async function onReprocess() {
    setReprocessing(true);
    await dispatch(reprocessComplaint(complaint.id));
    dispatch(fetchStats());
    dispatch(fetchSignals());
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
          <SlaBadge
            daysLeft={complaint.investigation_days_left}
            isOverdue={complaint.is_overdue}
          />
          <select className="status-select" value={complaint.status} onChange={onStatusChange}>
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

      <ReportabilityCard complaint={complaint} />

      {complaint.duplicate_of && (
        <div className="alert warn">
          <span>⚠️</span>
          <div>
            This looks like a possible duplicate of{" "}
            <Link to={`/complaints/${complaint.duplicate_of}`} className="ref">
              {complaint.duplicate_reference || `complaint #${complaint.duplicate_of}`}
            </Link>
            {complaint.duplicate_score
              ? ` (similarity ${Math.round(complaint.duplicate_score * 100)}%)`
              : ""}
            . Review before opening a new investigation.
          </div>
        </div>
      )}
      {complaint.processing_state === "failed" && (
        <div className="alert danger">
          <span>!</span>
          <div>
            AI analysis failed{complaint.processing_error ? `: ${complaint.processing_error}` : "."}
            {" "}Use Re-run AI to try again.
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

          <RiskBlock complaint={complaint} />

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

        <div>
          {related && related.count > 0 && <RelatedCard related={related} />}

          <div className="card" style={{ padding: 22, marginBottom: 16 }}>
            <h3 className="section-title">Original complaint</h3>
            <div className="source-box">{complaint.source_text}</div>
            {complaint.original_filename && (
              <p className="muted" style={{ marginTop: 10 }}>
                Source file: {complaint.original_filename}
              </p>
            )}
          </div>

          <div className="card" style={{ padding: 22 }}>
            <h3 className="section-title">Audit trail</h3>
            <ul className="timeline">
              {complaint.audit_events.map((event, i) => (
                <li key={i}>
                  <div className="t-action">{event.action}</div>
                  <div className="t-meta">
                    {event.actor} · {formatDate(event.created_at)}
                  </div>
                  {event.detail && <div className="t-detail">{event.detail}</div>}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function ReportabilityCard({ complaint }) {
  if (complaint.reportable === null || complaint.reportable === undefined) return null;

  if (!complaint.reportable) {
    return (
      <div className="reg-card clear">
        <div className="reg-head">✓ No regulatory report required</div>
        <div className="reg-detail">{complaint.report_reason}</div>
      </div>
    );
  }

  const days = complaint.report_days_left;
  const pillClass = days === null ? "warn" : days < 0 ? "danger" : days <= 2 ? "warn" : "ok";
  const dueText =
    days === null
      ? ""
      : days < 0
      ? `Overdue by ${Math.abs(days)} day(s)`
      : `Due in ${days} day(s)`;

  return (
    <div className="reg-card reportable">
      <div className="reg-head">🚨 Regulatory report likely required: {complaint.report_type}</div>
      <div className="reg-detail">{complaint.report_reason}</div>
      {complaint.report_due_at && (
        <span className={`due-pill ${pillClass}`}>
          Report due {formatDate(complaint.report_due_at)} · {dueText}
        </span>
      )}
    </div>
  );
}

function RiskBlock({ complaint }) {
  const dispatch = useDispatch();
  const [level, setLevel] = useState(complaint.risk_level || "Major");
  const [reason, setReason] = useState("");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  async function save() {
    if (reason.trim().length < 3) return;
    setSaving(true);
    await dispatch(overrideRisk({ id: complaint.id, risk_level: level, reason: reason.trim() }));
    dispatch(fetchStats());
    setSaving(false);
    setOpen(false);
    setReason("");
  }

  return (
    <div className="ai-block">
      <h4>
        Risk classification <span className="ai-tag">AI triage</span>
      </h4>
      <div style={{ marginBottom: 8, display: "flex", alignItems: "center", gap: 10 }}>
        <RiskBadge level={complaint.risk_level} />
        <button className="btn btn-ghost" style={{ padding: "4px 10px" }} onClick={() => setOpen(!open)}>
          {open ? "Cancel" : "Override"}
        </button>
      </div>
      <p className="ai-text">{complaint.risk_rationale || "No rationale available."}</p>

      {complaint.risk_overridden && (
        <div className="overridden-note">
          Overridden by QA. Original AI assessment: {complaint.ai_risk_level}.
        </div>
      )}

      {open && (
        <div className="override-box">
          <label>Change risk level (recorded in the audit trail)</label>
          <div className="override-row">
            <select className="status-select" value={level} onChange={(e) => setLevel(e.target.value)}>
              <option value="Critical">Critical</option>
              <option value="Major">Major</option>
              <option value="Minor">Minor</option>
            </select>
            <input
              type="text"
              placeholder="Reason for the change"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <button
              className="btn btn-primary"
              onClick={save}
              disabled={saving || reason.trim().length < 3}
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function RelatedCard({ related }) {
  const navigate = useNavigate();
  return (
    <div className="card" style={{ padding: 22, marginBottom: 16 }}>
      <h3 className="section-title">Related complaints (batch {related.batch_number})</h3>
      <p className="muted" style={{ margin: "0 0 4px" }}>
        {related.count} other complaint(s) reference this batch. Consider a batch level view.
      </p>
      <div className="related-list">
        {related.references.map((r) => (
          <div className="related-item" key={r.id}>
            <span className="ref" onClick={() => navigate(`/complaints/${r.id}`)}>
              {r.reference}
            </span>
            <RiskBadge level={r.risk_level} />
          </div>
        ))}
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
