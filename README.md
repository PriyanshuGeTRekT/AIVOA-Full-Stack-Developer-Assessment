# PharmaQMS - AI Powered Customer Complaint Management

An AI assisted Customer Complaint module for a pharmaceutical Quality Management
System (QMS). It takes a raw complaint (pasted text, an email, or an uploaded
PDF) about an API or finished dosage form (FDF) product and runs it through a
LangGraph agent that extracts the key fields, checks completeness, classifies
risk, flags likely duplicates, and drafts a root cause and CAPA for the QA
reviewer.

The whole thing runs end to end out of the box. If you set a Groq API key it
uses the `gemma2-9b-it` model for the reasoning steps; if you do not, it falls
back to a deterministic rule based engine so the workflow still works for a
demo or in CI.

---

## Why a complaint module

In a pharma QMS, a customer complaint is a formal quality record. Handling it
well matters for patient safety and for GMP compliance. The manual parts that
are slow and error prone are exactly the ones an LLM is good at:

- reading an unstructured email or PDF and pulling out product, batch and issue
- deciding how serious it is (critical / major / minor)
- spotting that "this is the third complaint about batch AMX-2405-118"
- suggesting a starting point for the investigation and the CAPA

This project automates that first pass and leaves the human QA reviewer in
control of the decision.

---

## Tech stack

| Layer            | Choice                                             |
| ---------------- | -------------------------------------------------- |
| Frontend         | React 18 + Redux Toolkit + Vite, Google Inter font |
| Backend          | Python + FastAPI                                    |
| AI orchestration | LangGraph                                           |
| LLM              | Groq `gemma2-9b-it` (via `langchain-groq`)          |
| Database         | Postgres (SQLAlchemy), SQLite fallback for local   |

---

## The AI workflow (LangGraph)

The agent lives in `backend/app/agent`. It is a single compiled graph that runs
the complaint through seven nodes in sequence. Each node reads the shared state
and writes back the piece it produced.

```
        ┌─────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐
START ─▶│ extract │─▶ │ completeness │─▶ │ classify_risk │─▶ │ detect_duplicate │─┐
        └─────────┘   └──────────────┘   └──────────────┘   └─────────────────┘ │
                                                                                 ▼
                    ┌────────────┐   ┌───────────────┐   ┌──────────────────────┐
             END ◀──│  summarise │◀─ │ recommend_capa│◀─ │ recommend_root_cause │
                    └────────────┘   └───────────────┘   └──────────────────────┘
```

| Node                   | What it does                                          | AI feature                     |
| ---------------------- | ----------------------------------------------------- | ------------------------------ |
| `extract`              | Parses raw text into structured fields                | Field extraction               |
| `check_completeness`   | Flags missing fields needed to investigate            | Complaint Completeness Checker |
| `classify_risk`        | Critical / Major / Minor with a rationale             | AI Risk Classification         |
| `detect_duplicate`     | Compares against existing complaints (no LLM)         | Duplicate Complaint Detection  |
| `recommend_root_cause` | Suggests a probable root cause                        | Root Cause Recommendation      |
| `recommend_capa`       | Drafts corrective and preventive actions              | CAPA Recommendation            |
| `summarise`            | One line summary for the dashboard                    | Complaint Summary              |

Design notes:

- **Every LLM node has a heuristic fallback.** The wrapper in `agent/llm.py`
  raises `LLMUnavailable` when there is no key or a call fails, and each node
  catches it and switches to a rule based path. That is what makes the app run
  without Groq.
- **Duplicate detection is deliberately not an LLM call.** It is a cheap,
  deterministic similarity comparison (shared batch number plus fuzzy match on
  product and description). Using an LLM there would be slower, non
  deterministic and harder to trust.
- **The graph is linear on purpose.** The steps genuinely depend on the
  extraction that runs first, so a straight pipeline is the honest, readable
  choice. The structure still makes branching easy to add later (for example,
  skipping CAPA when a complaint is flagged as a duplicate).

---

## Project layout

```
backend/
  app/
    main.py            FastAPI app, CORS, startup seed
    config.py          Settings from env / .env
    database.py        SQLAlchemy engine and session
    models.py          Complaint ORM model
    schemas.py         Pydantic request/response models
    crud.py            Database access helpers
    routers/
      complaints.py    All /api routes
    agent/
      graph.py         Builds and compiles the LangGraph
      state.py         Shared graph state (TypedDict)
      nodes.py         The seven node functions + heuristics
      llm.py           Groq wrapper with graceful fallback
      prompts.py       Prompt templates per node
    services/
      documents.py     Text extraction from PDF / email / txt
      processing.py    Runs the graph and persists the result
      seed.py          Sample complaints on first run
  sample_data/         Demo complaint files (eml, txt, pdf)
  requirements.txt
  .env.example
frontend/
  src/
    store/             Redux Toolkit slice and store
    api/client.js      Axios API layer
    components/        Sidebar, table, modal, badges, stat cards
    pages/             Dashboard and complaint detail
docker-compose.yml     Postgres for the production setup
```

---

## Getting started

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # optional: add your GROQ_API_KEY
uvicorn app.main:app --reload --port 8000
```

The API is now on `http://localhost:8000` (docs at `/docs`). On first run it
creates the tables and seeds a few sample complaints so the dashboard is not
empty.

To use Groq, get a key from https://console.groq.com/keys and put it in
`backend/.env` as `GROQ_API_KEY=...`. Without a key the app runs on the
heuristic fallback, which the sidebar shows as "Heuristic mode".

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to the
backend, so no extra configuration is needed.

### 3. Postgres (optional, production style)

```bash
docker compose up -d
# then set in backend/.env:
# DATABASE_URL=postgresql+psycopg2://qms:qms@localhost:5432/complaints
```

---

## Using it

1. Click **New complaint**.
2. Either paste a complaint (there are ready examples in
   `backend/sample_data`) or upload a file (`.pdf`, `.eml`, `.txt`).
3. The agent runs and you land on the detail view with the extracted fields,
   risk level, summary, duplicate warning, root cause and CAPA.
4. Move the complaint through **Open → Under review → Closed**, or hit
   **Re-run AI** (handy right after adding a Groq key).

### Sample files

`backend/sample_data` contains:

- `complaint_email_contamination.eml` - a discoloration complaint
- `complaint_packaging.txt` - a seal integrity complaint
- `complaint_form.pdf` - a broken tablet complaint form
- `make_sample_pdf.py` - regenerates the PDF (needs `reportlab`)

---

## API reference

| Method | Path                              | Purpose                          |
| ------ | --------------------------------- | -------------------------------- |
| GET    | `/api/health`                     | Status and current LLM mode      |
| GET    | `/api/stats`                      | Dashboard counters               |
| GET    | `/api/complaints`                 | List (worklist rows)             |
| GET    | `/api/complaints/{id}`            | Full complaint record            |
| POST   | `/api/complaints`                 | Create from pasted text          |
| POST   | `/api/complaints/upload`          | Create from an uploaded file     |
| PATCH  | `/api/complaints/{id}/status`     | Move through the workflow        |
| POST   | `/api/complaints/{id}/reprocess`  | Re-run the agent                 |

---

## Key design decisions

- **Graceful degradation over hard dependency.** The reviewer stressed a
  workflow that works end to end. Making the LLM optional (heuristic fallback)
  guarantees that, and reprocessing lets you upgrade a record once Groq is on.
- **SQLite default, Postgres ready.** SQLAlchemy means one line in `.env`
  swaps the database. SQLite keeps local setup to zero, Postgres is there for
  the mandated production stack.
- **Synchronous processing for a clean demo.** The create and upload endpoints
  run the agent before responding, so the UI gets the finished record in one
  round trip. `processing_state` on the model is the seam where this would move
  to a background worker for higher volumes.
- **Agent output stored on the complaint row.** One read gives the UI the whole
  picture, which keeps the frontend simple.

## Note on the code

Written with AI assistance per the assignment, then reviewed, adapted and
tested by hand. The heuristic extractors in particular were tuned against the
sample complaints (batch code parsing, word boundary keyword matching, and
score based type detection) rather than left as first draft output.
