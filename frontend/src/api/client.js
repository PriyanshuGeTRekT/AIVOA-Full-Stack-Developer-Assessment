import axios from "axios";

// One axios instance for the whole app. The base URL is empty because the Vite
// dev server proxies /api straight to FastAPI (see vite.config.js). In a real
// deployment you would point this at the API host via an env variable.
const client = axios.create({
  baseURL: "",
  headers: { "Content-Type": "application/json" },
});

export const complaintsApi = {
  list: () => client.get("/api/complaints").then((r) => r.data),
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
  reprocess: (id) => client.post(`/api/complaints/${id}/reprocess`).then((r) => r.data),
};

export default client;
