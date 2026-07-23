import { useEffect, useState } from "react";

import client from "../api/client";

// The sidebar is mostly static, but it also surfaces which LLM mode the backend
// is running in. That transparency is useful during a demo: you can see at a
// glance whether Groq is wired up or the heuristic fallback is in play.
export default function Sidebar() {
  const [llmMode, setLlmMode] = useState(null);

  useEffect(() => {
    client
      .get("/api/health")
      .then((r) => setLlmMode(r.data.llm_mode))
      .catch(() => setLlmMode(null));
  }, []);

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">Rx</span>
        PharmaQMS
      </div>

      <nav className="nav">
        <div className="nav-item active">
          <span>📋</span> Complaints
        </div>
        <div className="nav-item">
          <span>🔬</span> Investigations
        </div>
        <div className="nav-item">
          <span>🛠️</span> CAPA
        </div>
        <div className="nav-item">
          <span>📊</span> Reports
        </div>
      </nav>

      <div className="sidebar-footer">
        {llmMode && (
          <div className={`llm-pill ${llmMode === "heuristic" ? "heuristic" : ""}`}>
            <span>●</span>
            {llmMode === "groq" ? "Groq gemma2-9b-it" : "Heuristic mode"}
          </div>
        )}
        <div>Customer Complaint Module</div>
        <div>Quality Management System</div>
      </div>
    </aside>
  );
}
