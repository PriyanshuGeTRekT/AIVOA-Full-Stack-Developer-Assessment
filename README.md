# PharmaQMS - AI Powered Customer Complaint Management

An AI assisted Customer Complaint module for a pharmaceutical Quality Management
System (QMS). It takes a raw complaint (pasted text, an email, or an uploaded
PDF) about an API or finished dosage form (FDF) product and runs it through a
LangGraph agent that extracts the key fields, checks completeness, classifies
risk, decides whether it is a reportable regulatory event, flags likely
duplicates, and drafts a root cause and CAPA for the QA reviewer.

It goes beyond "read the complaint and fill a form". It targets the four things
that actually hurt a pharma quality team:

1. **Missed reporting deadlines.** The agent flags when a complaint likely
   triggers a mandatory report (FDA Field Alert Report, or Pharmacovigilance for
   an adverse event) and computes the deadline, counting working days.
2. **Systemic batch problems seen too late.** A trend detector watches across
   complaints and raises a quality signal when several point at the same batch
   or the same product defect, which is what GMP complaint trending is for.
3. **Investigations aging past their SLA.** Each complaint gets an investigation
   due date from its risk level, and overdue records are surfaced.
4. **Unreviewable AI decisions.** A QA reviewer can override the AI risk level
   with a recorded reason, and every meaningful change is written to an audit
   trail. The AI advises; the human decides.

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
the complaint through eight nodes in sequence. Each node reads the shared state
and writes back the piece it produced.

```
  extract -> check_completeness -> classify_risk -> assess_reportability
          -> detect_duplicate -> recommend_root_cause -> recommend_capa -> summarise
```

| Node                   | What it does                                          | AI feature                     |
| ---------------------- | ----------------------------------------------------- | ------------------------------ |
| `extract`              | Parses raw text into structured fields                | Field extraction               |
| `check_completeness`   | Flags missing fields needed to investigate            | Complaint Completeness Checker |
| `classify_risk`        | Critical / Major / Minor with a rationale             | AI Risk Classification         |
| `assess_reportability` | Decides FDA Field Alert / Pharmacovigilance / None    | Regulatory reportability       |
| `detect_duplicate`     | Compares against existing complaints (no LLM)         | Duplicate Complaint Detection  |
| `recommend_root_cause` | Suggests a probable root cause                        | Root Cause Recommendation      |
| `recommend_capa`       | Drafts corrective and preventive actions              | CAPA Recommendation            |
| `summarise`            | One line summary for the dashboard                    | Complaint Summary              |

Two more AI features live outside the per-complaint graph because they only make
sense across the whole dataset or need a human in the loop:

- **Trend / signal detection** (`services/signals.py`) runs across all
  complaints and raises a quality signal when a batch or a product/defect pair
  crosses a threshold. Duplicate detection asks "same complaint twice?"; this
  asks "same underlying problem across many complaints?".
- **Human override with audit trail** lets QA overrule the AI risk level with a
  reason. The original AI call is preserved and the change is logged.

The regulatory *deadlines* themselves are computed by pure, testable functions
in `app/regulatory.py` (for example, a Field Alert Report is due 3 working days
from receipt). The AI decides the category; deterministic code decides the date.

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
    regulatory.py      Pure deadline math (Field Alert, PV, investigation SLA)
    agent/
      graph.py         Builds and compiles the LangGraph
      state.py         Shared graph state (TypedDict)
      nodes.py         The eight node functions + heuristics
      llm.py           Groq wrapper with graceful fallback
      prompts.py       Prompt templates per node
    services/
      documents.py     Text extraction from PDF / email / txt
      processing.py    Runs the graph and persists the result
      signals.py       Cross complaint trend / signal detection
      seed.py          Sample complaints on first run (incl. a batch cluster)
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
| GET    | `/api/signals`                    | Detected cross complaint trends  |
| GET    | `/api/complaints`                 | List (worklist rows)             |
| GET    | `/api/complaints/{id}`            | Full complaint record            |
| GET    | `/api/complaints/{id}/related`    | Other complaints on same batch   |
| POST   | `/api/complaints`                 | Create from pasted text          |
| POST   | `/api/complaints/upload`          | Create from an uploaded file     |
| PATCH  | `/api/complaints/{id}/status`     | Move through the workflow        |
| PATCH  | `/api/complaints/{id}/risk`       | Human override of AI risk level  |
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
- **AI decides categories, deterministic code decides deadlines.** Reportability
  type comes from the agent; the actual due dates come from `regulatory.py`. You
  never want a language model doing date arithmetic on a legal deadline.
- **Trend detection is not an LLM call, and neither is duplicate detection.**
  Both are cheap, deterministic and explainable. In a regulated setting, "why
  did it flag this" needs a clear answer, and a similarity score gives one.
- **Human in the loop is a first class feature, not an afterthought.** GMP does
  not allow an algorithm to be the final decision maker on a quality event, so
  override plus audit trail is built in rather than bolted on.

## Domain modelling choices (and their caveats)

The regulatory windows in `regulatory.py` (Field Alert 3 working days,
expedited PV 15 calendar days, investigation SLAs by risk) are realistic
defaults, not legal advice. They are named constants in one file precisely
because a real site would set them from its own SOPs. The reportability and
risk logic are decision support: they are tuned to be sensitive (better to flag
one report too many than miss one), and the human override exists for the cases
where the AI is wrong.

## Note on the code

Written with AI assistance per the assignment, then reviewed, adapted and
tested by hand. The heuristic extractors in particular were tuned against the
sample complaints (batch code parsing, word boundary keyword matching, and
score based type detection) rather than left as first draft output.
