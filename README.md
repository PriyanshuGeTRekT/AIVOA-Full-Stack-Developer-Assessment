# PharmaQMS - Customer Complaint Module

AI-assisted customer complaint handling for a pharma QMS. Paste text or upload a PDF/email, run a LangGraph agent, then review risk, reportability, duplicates, root cause, and CAPA in the UI.

Works without an LLM key (heuristic fallback). With `GROQ_API_KEY` it uses Groq for the reasoning steps.

## What it covers

- Field extraction, completeness check, risk, reportability, root cause, CAPA, summary
- Duplicate detection (deterministic similarity, no LLM)
- Quality signals when several complaints share a batch or product/defect
- Investigation SLAs and report due dates (`regulatory.py`)
- Human risk override with audit trail

## Stack

| Layer | Choice |
| ----- | ------ |
| Frontend | React 18, Redux Toolkit, Vite |
| Backend | FastAPI, SQLAlchemy |
| Agent | LangGraph + Groq (`langchain-groq`) |
| DB | SQLite by default, Postgres via Docker |

## Agent pipeline

```
extract -> completeness -> risk -> reportability -> duplicate
       -> root_cause -> capa -> summary
```

Strong duplicates skip root cause/CAPA and go straight to summary.

| Node | Role |
| ---- | ---- |
| `extract` | Structured fields from raw text |
| `check_completeness` | Missing fields for investigation |
| `classify_risk` | Critical / Major / Minor |
| `assess_reportability` | Field Alert / PV / None |
| `detect_duplicate` | Match against existing rows (no LLM) |
| `recommend_root_cause` | Suggested root cause |
| `recommend_capa` | Corrective + preventive draft |
| `summarise` | One-line dashboard summary |

Outside the graph:

- Trends: `services/signals.py`
- Deadlines: `regulatory.py` (AI picks category, code sets the date)
- Override: PATCH risk + audit event

Each LLM node falls back to heuristics if Groq is missing or fails.

## Layout

```
backend/
  app/
    main.py, config.py, database.py, models.py, schemas.py, crud.py
    regulatory.py
    routers/complaints.py
    agent/          # graph, nodes, llm, prompts, state
    services/       # documents, processing, signals, seed
  sample_data/
  alembic/          # optional migrations for Postgres
  tests/
frontend/
  src/              # pages, components, store, api
docker-compose.yml  # Postgres (+ optional full stack profile)
```

## Setup

### Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # optional: GROQ_API_KEY=...
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  

First boot creates tables and seeds sample complaints (including a batch cluster for signals).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the backend.

### Postgres (optional)

```bash
docker compose up -d db
# backend/.env:
# DATABASE_URL=postgresql+psycopg2://qms:qms@localhost:5432/complaints
```

For schema changes against Postgres: `cd backend && alembic upgrade head`.

## Usage

1. **New complaint** - paste text or upload from `backend/sample_data`
2. Open the detail page for extraction, risk, CAPA, audit trail
3. Change status, override risk, or **Re-run AI**
4. Use worklist filters / stat cards; watch quality signals on the dashboard

Sample files:

- `complaint_email_contamination.eml`
- `complaint_packaging.txt`
- `complaint_form.pdf`
- `make_sample_pdf.py` (needs `reportlab` to regenerate)

## API

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/health` | Health, LLM mode, DB status |
| GET | `/api/stats` | Dashboard counters |
| GET | `/api/signals` | Trend signals |
| GET | `/api/complaints` | List (filters, search, pagination) |
| GET | `/api/complaints/{id}` | Full record |
| GET | `/api/complaints/{id}/related` | Same batch |
| POST | `/api/complaints` | Create from text |
| POST | `/api/complaints/upload` | Create from file |
| PATCH | `/api/complaints/{id}/status` | Status change |
| PATCH | `/api/complaints/{id}/risk` | Risk override |
| POST | `/api/complaints/{id}/reprocess` | Re-run agent |

Create/upload process in the background by default (`SYNC_PROCESSING=false`). The UI polls `processing_state`. Set `SYNC_PROCESSING=true` for in-request processing (used in tests).

## Design notes

- LLM is optional; heuristics keep demos and CI green
- SQLite for local, Postgres for a production-style stack
- Report category from the agent; due dates only from `regulatory.py`
- Duplicates and trends are deterministic (easier to explain than an LLM score)
- QA can override risk; reprocess keeps the override and updates `ai_risk_level`
- Status changes follow a small transition map

Deadlines in `regulatory.py` are demo defaults (e.g. Field Alert 3 working days, PV 15 calendar days), not legal advice. Real sites would load SOP windows.

## Tests

```bash
cd backend
pytest -q
```

## Notes

Built for the assignment with AI assistance, then reviewed and tested by hand. Heuristics were tuned against the sample complaints (batch labels, word boundaries, negation, type scoring).
