# PharmaQMS Demo Video Script

**Target duration:** 12–13 minutes  
**Required duration:** 10–15 minutes  
**Recording format:** Screen recording with voice-over  
**Before recording:** Start the backend and frontend, confirm `/api/health` reports `llm_mode: groq`, and keep the repository open in an editor.

## Recording preparation

Have these tabs and files ready:

1. GitHub repository landing page
2. Running frontend at `http://localhost:5173`
3. FastAPI docs at `http://localhost:8000/docs`
4. `backend/sample_data/complaint_email_contamination.eml`
5. `backend/app/agent/graph.py`
6. `backend/app/agent/nodes.py`
7. `backend/app/services/processing.py`
8. `frontend/src/store/complaintsSlice.js`
9. `backend/app/regulatory.py`
10. `backend/app/services/signals.py`

Use a clean seeded database if possible so the dashboard initially shows the six sample complaints and at least one batch quality signal.

---

## 0:00–0:45 — Introduction and repository

### Screen

Show the GitHub repository and briefly scroll through the top of the README.

### Narration

> Hello, this is PharmaQMS, my full-stack developer assessment project. It is an AI-assisted pharmaceutical customer-complaint management system built with React, FastAPI, SQLAlchemy, LangGraph, and Groq.
>
> The repository contains the complete source code, setup instructions, tests, GitHub Actions CI, Docker configuration, database migrations, sample complaint files, and this demo guide.
>
> The main goal is to convert an unstructured customer complaint into a structured, reviewable, and auditable quality workflow while keeping a human reviewer in control of final decisions.

---

## 0:45–1:40 — Problem and solution overview

### Screen

Show the README’s “Project overview” and “Implemented capabilities” sections.

### Narration

> A pharmaceutical complaint may arrive as an email, PDF, or pasted note. Manually extracting fields and deciding what needs immediate attention is slow and inconsistent.
>
> PharmaQMS accepts that unstructured input and performs field extraction, completeness checking, risk classification, reportability assessment, duplicate detection, root-cause drafting, CAPA drafting, and summary generation.
>
> I intentionally use a hybrid design. Language models handle interpretation and drafting. Deterministic code handles deadlines, status transitions, duplicate scoring, and quality-signal thresholds, where repeatability and explainability are more important than generative flexibility.

---

## 1:40–2:40 — Frontend dashboard

### Screen

Open `http://localhost:5173`. Point to:

- Sidebar
- Statistic cards
- Quality signals
- Search and filters
- Complaint table

### Narration

> This is the main worklist. The statistic cards summarise total, open, review, critical, reportable, and overdue complaints. Clicking a card can narrow the worklist.
>
> The quality-signal panel detects repeated complaints for a batch or repeated product-and-defect combinations. This is deterministic trend detection rather than an LLM guess.
>
> The worklist supports search, status and risk filters, reportability and overdue filters, sorting, and pagination. Redux Toolkit owns the client state, and async thunks call the FastAPI backend through a shared Axios client.

---

## 2:40–4:25 — Create a complaint and show AI processing

### Screen

Select **New Complaint** and paste this prepared example:

```text
From: Anita Rao
Email: anita.rao@example.com
Product: CardioRelief 50 mg tablets
Batch/Lot: CR-2407

The bottle seal was broken when opened and several tablets had dark particles.
The patient took one tablet and developed nausea and dizziness. No hospitalisation
was required. Please investigate the possible contamination.
```

Submit it. Show the processing state, then open the completed complaint.

### Narration

> I’ll create a complaint containing packaging damage, possible contamination, and an adverse event. The API first creates a database record with a pending state and returns quickly.
>
> Processing runs in the background. The frontend polls the complaint endpoint until the state becomes done or failed, so the interface stays responsive during model calls.
>
> The completed record contains the extracted product, batch, complainant, contact, complaint type, and description. It also shows the completeness result, risk level with rationale, and reportability recommendation.
>
> Because this example contains possible contamination and patient symptoms, the workflow can identify both quality and pharmacovigilance concerns. These outputs are recommendations for review, not autonomous regulatory decisions.

---

## 4:25–5:35 — Root cause, CAPA, duplicates, and auditability

### Screen

Scroll through the complaint detail page:

- Summary
- Risk block
- Reportability card
- Completeness
- Root cause
- CAPA
- Related complaints
- Audit trail

### Narration

> The root-cause section provides an investigation direction, while CAPA separates immediate corrective action from longer-term preventive action.
>
> Duplicate detection compares the new record with existing complaints using weighted text similarity and structured fields. A strong duplicate takes a conditional route in the graph and skips redundant root-cause and CAPA generation.
>
> The audit timeline records complaint creation, AI analysis, status updates, reprocessing, and human overrides. This supports traceability and makes it clear which conclusions came from AI and which came from a reviewer.

---

## 5:35–6:35 — Human review workflow

### Screen

Change the complaint from **Open** to **Under Review**. Demonstrate the risk override dialog, but use an appropriate reason such as:

```text
QA review confirms visible foreign particles; upgraded per site escalation SOP.
```

Optionally click **Re-run AI** after showing the override.

### Narration

> The status workflow only allows defined transitions: open to under review, then under review to closed, with reopening where configured. Invalid jumps return a conflict response.
>
> A QA reviewer can override risk by entering a reviewer name and justification. The application preserves the AI-generated baseline separately, records the human-selected risk, and adds an audit event.
>
> If the analysis is re-run later, the new AI baseline is saved, but the human override remains authoritative. That is an important safety decision: reprocessing cannot silently undo a reviewed decision.

---

## 6:35–7:35 — End-to-end code flow

### Screen

Show the architecture diagram in the README, then briefly open:

- `frontend/src/api/client.js`
- `backend/app/routers/complaints.py`
- `backend/app/services/processing.py`

### Narration

> The end-to-end flow begins in React. A Redux async thunk calls the Axios API client. Vite proxies the `/api` path to FastAPI during development.
>
> The complaint router validates the request, creates the database row through the CRUD layer, and either processes synchronously for tests or adds a FastAPI background task for normal use.
>
> The processing service owns the application-level workflow. It marks the complaint as processing, loads existing rows for duplicate comparison, invokes LangGraph, maps the resulting graph state onto the SQLAlchemy model, calculates deterministic deadlines, records an audit event, and commits the result.

---

## 7:35–9:25 — LangGraph implementation

### Screen

Open `backend/app/agent/graph.py`. Trace each node and the conditional edge. Then open `backend/app/agent/state.py`.

### Narration

> LangGraph coordinates the AI workflow as explicit, testable steps instead of using one large prompt.
>
> The graph starts with extraction, then checks completeness, classifies risk, assesses reportability, and performs duplicate detection.
>
> The duplicate node has a conditional edge. When a strong match exists, execution moves to `skip_investigation` and then summary. Otherwise, it continues through root-cause and CAPA recommendation before summary.
>
> The shared typed state contains the raw text, existing complaint candidates, extracted fields, completeness result, risk and reportability outputs, duplicate information, RCA, CAPA, summary, and whether an LLM was used.
>
> This graph structure gives each responsibility a clear boundary, makes routing visible, and lets individual nodes be tested or replaced independently.

---

## 9:25–10:35 — Groq integration and AI fallbacks

### Screen

Open:

- `backend/app/agent/llm.py`
- Relevant portions of `backend/app/agent/nodes.py`
- `backend/app/agent/prompts.py`

### Narration

> The LLM wrapper reads the model and key from environment-backed settings. It calls the primary Groq model first and can retry with a configured fallback model.
>
> JSON responses are parsed defensively because a model may add Markdown fences or surrounding text.
>
> Each LLM-backed node catches an unavailable or invalid model response and switches to a domain-specific heuristic. For example, risk rules use word boundaries and negation handling, while extraction recognises product and batch labels.
>
> This means missing credentials, network errors, rate limits, decommissioned models, or malformed JSON do not break the entire complaint workflow. The health endpoint exposes whether the running application is in Groq or heuristic mode without exposing the key.

---

## 10:35–11:35 — Deterministic regulatory and trend logic

### Screen

Open:

- `backend/app/regulatory.py`
- `backend/app/services/signals.py`
- `backend/app/crud.py`

### Narration

> I keep regulatory date calculation outside the model. The AI can recommend a category, but application code converts that category into a due date using explicit working-day or calendar-day rules.
>
> Quality signals also use deterministic grouping and thresholds. Complaints are grouped by batch and by product-and-defect combination, then ranked using the highest member risk.
>
> CRUD functions centralise search, sorting, pagination, status transitions, risk overrides, dashboard statistics, and audit creation. This keeps route handlers focused on HTTP concerns.
>
> The deadlines in this assessment are demonstration defaults. A production site would load approved SOP and jurisdiction-specific rules.

---

## 11:35–12:25 — Database, tests, and deployment

### Screen

Show:

- `backend/app/models.py`
- `backend/tests/`
- `.github/workflows/ci.yml`
- `docker-compose.yml`

Optionally show a terminal with:

```bash
cd backend
pytest -q
```

### Narration

> SQLAlchemy models store the complaint, AI outputs, human override fields, processing state, deadlines, and related audit events.
>
> SQLite provides a zero-setup local experience. PostgreSQL, Alembic migrations, Dockerfiles, and Docker Compose provide a more production-like deployment path.
>
> The test suite covers agent heuristics, the complete graph result shape, API creation and filtering, status conflicts, risk-override persistence, regulatory dates, uploads, and quality signals.
>
> GitHub Actions installs backend and frontend dependencies, runs Pytest in deterministic heuristic mode, and verifies the Vite production build without requiring repository secrets.

---

## 12:25–13:15 — Key decisions, limitations, and close

### Screen

Return to the README’s “Key design decisions” and “Important limitations” sections.

### Narration

> The key design decisions are hybrid AI and deterministic logic, graceful model fallback, human authority over AI, background processing, conditional LangGraph routing, explainable outputs, and portable persistence.
>
> Current limitations include no authentication or role-based access control, lexical rather than embedding-based duplicate detection, no OCR for image-only uploads, and in-memory file parsing. Regulatory recommendations and deadlines must be validated against approved procedures before real use.
>
> In summary, PharmaQMS demonstrates a complete AI-assisted complaint workflow while keeping critical quality decisions observable, auditable, and reviewable. Thank you for watching.

---

## Optional timing adjustments

If the recording is shorter than 10 minutes:

- Show the PDF or email upload workflow.
- Open FastAPI Swagger docs and demonstrate `/api/health` or `/api/signals`.
- Briefly show a failed invalid status transition.
- Explain one test from `test_agent.py` and one from `test_api.py`.

If the recording is longer than 15 minutes:

- Shorten the repository structure section.
- Show only one complaint intake method.
- Summarise the database, CI, and deployment section without opening every file.

## Final recording checklist

- Repository URL is visible.
- README setup instructions are shown.
- Health endpoint reports Groq mode.
- One complaint is created and processed.
- All AI-assisted outputs are explained.
- Dashboard and detail-page workflow are demonstrated.
- End-to-end code flow is described.
- LangGraph nodes and conditional routing are shown.
- Human override and auditability are explained.
- Key design decisions and limitations are stated.
- Final video length is between 10 and 15 minutes.
