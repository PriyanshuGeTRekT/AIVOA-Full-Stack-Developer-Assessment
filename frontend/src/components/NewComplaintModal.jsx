import { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";

import {
  clearSubmitStatus,
  fetchSignals,
  fetchStats,
  submitFileComplaint,
  submitTextComplaint,
} from "../store/complaintsSlice";

export default function NewComplaintModal({ onClose }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const dialogRef = useRef(null);

  const [tab, setTab] = useState("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);

  const submitStatus = useSelector((s) => s.complaints.submitStatus);
  const error = useSelector((s) => s.complaints.error);
  const submitting = submitStatus === "loading";

  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape" && !submitting) onClose();
    }
    window.addEventListener("keydown", onKey);
    dialogRef.current?.querySelector("textarea, button")?.focus?.();
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, submitting]);

  useEffect(() => {
    dispatch(clearSubmitStatus());
  }, [dispatch]);

  async function handleSubmit() {
    const action =
      tab === "text"
        ? submitTextComplaint(text.trim())
        : submitFileComplaint(file);

    const result = await dispatch(action);
    if (result.meta.requestStatus === "fulfilled") {
      dispatch(fetchStats());
      dispatch(fetchSignals());
      dispatch(clearSubmitStatus());
      onClose();
      navigate(`/complaints/${result.payload.id}`);
    }
  }

  const canSubmit =
    !submitting && (tab === "text" ? text.trim().length >= 5 : Boolean(file));

  return (
    <div
      className="modal-backdrop"
      onClick={() => !submitting && onClose()}
      role="presentation"
    >
      <div
        className="modal"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-complaint-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="new-complaint-title">Log a customer complaint</h2>
        <p className="hint">
          Paste the complaint text or upload the source document. The AI agent
          will extract the details, assess risk and suggest next steps.
        </p>

        <div className="tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "text"}
            className={`tab ${tab === "text" ? "active" : ""}`}
            onClick={() => setTab("text")}
          >
            Paste text
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "upload"}
            className={`tab ${tab === "upload" ? "active" : ""}`}
            onClick={() => setTab("upload")}
          >
            Upload file
          </button>
        </div>

        {tab === "text" ? (
          <textarea
            rows={9}
            placeholder="e.g. We received Amoxicillin 500mg, batch AMX-2405-118, with black particles inside several capsules..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        ) : (
          <div
            className="dropzone"
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.eml,.md,.csv,.png,.jpg,.jpeg"
              style={{ display: "none" }}
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            {file ? (
              <div>
                <strong>{file.name}</strong>
                <div className="muted">Click to choose a different file</div>
              </div>
            ) : (
              <div>
                <strong>Click to choose a file</strong>
                <div className="muted">PDF, EML or TXT complaint document (max 5 MB)</div>
              </div>
            )}
          </div>
        )}

        {error && <div className="error-text">Something went wrong: {error}</div>}

        <div className="modal-actions">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onClose}
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={!canSubmit}
          >
            {submitting ? (
              <>
                <span className="spinner" /> Analysing...
              </>
            ) : (
              "Run AI analysis"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
