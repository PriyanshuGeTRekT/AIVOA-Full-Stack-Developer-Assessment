import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { complaintsApi } from "../api/client";

export default function Sidebar() {
  const [llmMode, setLlmMode] = useState(null);
  const [dbStatus, setDbStatus] = useState(null);
  const location = useLocation();
  const onComplaints = location.pathname === "/" || location.pathname.startsWith("/complaints");

  useEffect(() => {
    complaintsApi
      .health()
      .then((data) => {
        setLlmMode(data.llm_mode);
        setDbStatus(data.database);
      })
      .catch(() => {
        setLlmMode(null);
        setDbStatus("down");
      });
  }, []);

  return (
    <aside className="sidebar">
      <Link to="/" className="brand">
        <span className="brand-mark">Rx</span>
        PharmaQMS
      </Link>

      <nav className="nav" aria-label="Primary">
        <Link to="/" className={`nav-item ${onComplaints ? "active" : ""}`}>
          <span>📋</span> Complaints
        </Link>
        <div className="nav-item disabled" title="Planned module">
          <span>🔬</span> Investigations
          <span className="soon-tag">Soon</span>
        </div>
        <div className="nav-item disabled" title="Planned module">
          <span>🛠️</span> CAPA
          <span className="soon-tag">Soon</span>
        </div>
        <div className="nav-item disabled" title="Planned module">
          <span>📊</span> Reports
          <span className="soon-tag">Soon</span>
        </div>
      </nav>

      <div className="sidebar-footer">
        {llmMode && (
          <div className={`llm-pill ${llmMode === "heuristic" ? "heuristic" : ""}`}>
            <span>●</span>
            {llmMode === "groq" ? "Groq LLM" : "Heuristic mode"}
          </div>
        )}
        {dbStatus === "down" && (
          <div className="llm-pill heuristic">
            <span>●</span>
            Backend unreachable
          </div>
        )}
        <div>Customer Complaint Module</div>
        <div>Quality Management System</div>
      </div>
    </aside>
  );
}
