import axios from "axios";

// Empty base URL in dev (Vite proxies /api). Set VITE_API_BASE_URL for static deploys.
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
  headers: { "Content-Type": "application/json" },
});

export const complaintsApi = {
  list: (params = {}) =>
    client.get("/api/complaints", { params }).then((r) => r.data),
  get: (id) => client.get(`/api/complaints/${id}`).then((r) => r.data),
  stats: () => client.get("/api/stats").then((r) => r.data),
  createFromText: (source_text) =>
    client.post("/api/complaints", { source_text }).then((r) => r.data),
  createFromFile: (file) => {
    const form = new FormData();
    form.append("file", file);
    return client
      .post("/api/complaints/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  updateStatus: (id, status) =>
    client.patch(`/api/complaints/${id}/status`, { status }).then((r) => r.data),
  overrideRisk: (id, risk_level, reason, actor) =>
    client
      .patch(`/api/complaints/${id}/risk`, { risk_level, reason, actor })
      .then((r) => r.data),
  reprocess: (id) => client.post(`/api/complaints/${id}/reprocess`).then((r) => r.data),
  signals: () => client.get("/api/signals").then((r) => r.data),
  related: (id) => client.get(`/api/complaints/${id}/related`).then((r) => r.data),
  health: () => client.get("/api/health").then((r) => r.data),
};

// Poll until processing_state is done/failed or we time out.
export async function waitForProcessing(id, { intervalMs = 800, timeoutMs = 120000 } = {}) {
  const started = Date.now();
  while (true) {
    const complaint = await complaintsApi.get(id);
    if (complaint.processing_state === "done" || complaint.processing_state === "failed") {
      return complaint;
    }
    if (Date.now() - started > timeoutMs) {
      throw new Error("Timed out waiting for AI analysis");
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

export default client;
