# PharmaQMS — AI-Assisted Customer Complaint Management

PharmaQMS is a full-stack pharmaceutical quality-management application for receiving, analysing, and investigating product complaints. A user can paste complaint text or upload a PDF, email, or text file; the backend then runs a LangGraph workflow that extracts structured data, assesses risk and regulatory reportability, checks for duplicates, and drafts root-cause and CAPA recommendations.

## Submission

- **GitHub repository:** [PriyanshuGeTRekT/AIVOA-Full-Stack-Developer-Assessment](https://github.com/PriyanshuGeTRekT/AIVOA-Full-Stack-Developer-Assessment)
- **Demo video:** Add the recorded video link here
- **Recording guide:** [VIDEO_DEMO_SCRIPT.md](./VIDEO_DEMO_SCRIPT.md)

## Project overview

The application turns unstructured customer complaints into an auditable quality workflow:

1. A complaint is entered as text or uploaded as a supported document.
2. FastAPI creates a complaint record and starts background processing.
3. LangGraph runs the complaint through specialised analysis nodes.
4. AI-assisted outputs and deterministic checks are saved to the database.
5. The React client polls for completion and presents the result for human review.
6. QA can update status, override risk with a reason, inspect related complaints, and re-run the analysis.

The application works in two modes:

- **Groq mode:** uses Groq-hosted language models for reasoning and drafting.
- **Heuristic fallback:** runs deterministic domain rules if no key is configured or an LLM call fails.

The fallback keeps local development, demos, and CI reliable. It is not presented as a substitute for validated pharmaceutical procedures or qualified human review.

## Implemented capabilities

### AI-assisted complaint analysis

| Capability | Implementation |
| --- | --- |
| Field extraction | Converts raw complaint text into product, batch, complainant, type, and description fields |
| Completeness check | Identifies missing investigation information |
| Risk classification | Classifies complaints as Critical, Major, or Minor with a rationale |
| Reportability assessment | Suggests Field Alert, Pharmacovigilance, or no report |
| Root-cause recommendation | Drafts a likely investigation direction |
| CAPA recommendation | Drafts corrective and preventive actions |
| Summary generation | Produces a concise dashboard summary |

### Deterministic quality controls

| Capability | Why it is deterministic |
| --- | --- |
| Duplicate detection | Similarity scoring is reproducible and explainable |
| Quality signals | Batch and product/defect clusters use explicit thresholds |
| Regulatory deadlines | Dates are calculated in application code, not invented by the LLM |
| Status transitions | A defined transition map prevents invalid workflow jumps |
| Human risk override | Preserves the AI baseline and records the reviewer, reason, and audit event |

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, Redux Toolkit, React Router, Axios, Vite |
| Backend | FastAPI, Pydantic, SQLAlchemy |
| Agent orchestration | LangGraph |
| LLM integration | Groq through `langchain-groq` |
| Local database | SQLite |
| Production-style database | PostgreSQL |
| Migrations | Alembic |
| Deployment | Docker and Docker Compose |
| Testing and CI | Pytest, GitHub Actions, Vite production build |

## Architecture and code flow

```mermaid
flowchart LR
    UI["React UI"] --> Store["Redux async thunks"]
    Store --> API["Axios /api client"]
    API --> Router["FastAPI complaint routes"]
    Router --> CRUD["CRUD and validation"]
    CRUD --> DB[("SQLite / PostgreSQL")]
    Router --> Job["Background processing"]
    Job --> Graph["LangGraph workflow"]
    Graph --> LLM["Groq LLM"]
    Graph --> Rules["Deterministic fallbacks and checks"]
    LLM --> Persist["Persist analysis"]
    Rules --> Persist
    Persist --> DB
    DB --> Router
    Router --> API
```

For a new complaint:

```text
POST /api/complaints or /api/complaints/upload
  -> create database row with processing_state=pending
  -> enqueue process_complaint_by_id
  -> processing_state=processing
  -> invoke LangGraph
  -> calculate deterministic deadlines and signals
  -> persist analysis and audit event
  -> processing_state=done (or failed)
  -> frontend polling receives the completed complaint
```

## LangGraph workflow

```mermaid
flowchart TD
    Start([START]) --> Extract[extract]
    Extract --> Complete[check_completeness]
    Complete --> Risk[classify_risk]
    Risk --> Report[assess_reportability]
    Report --> Duplicate[detect_duplicate]
    Duplicate -->|No strong match| Root[recommend_root_cause]
    Root --> CAPA[recommend_capa]
    CAPA --> Summary[summarise]
    Duplicate -->|Strong match| Skip[skip_investigation]
    Skip --> Summary
    Summary --> End([END])
```

| Node | Responsibility |
| --- | --- |
| `extract` | Build structured complaint fields from the source text |
| `check_completeness` | Identify missing information required for investigation |
| `classify_risk` | Produce risk level and supporting rationale |
| `assess_reportability` | Suggest reportability category and reason |
| `detect_duplicate` | Compare against existing complaints using deterministic similarity |
| `recommend_root_cause` | Draft a likely root-cause direction |
| `recommend_capa` | Draft corrective and preventive actions |
| `skip_investigation` | Avoid redundant RCA/CAPA generation for a strong duplicate |
| `summarise` | Produce the final concise complaint summary |

Every LLM-backed node catches model failures and uses its heuristic implementation. The graph state records all intermediate outputs and whether an LLM was used.

## Repository structure

```text
.
├── .github/workflows/ci.yml
├── backend/
│   ├── app/
│   │   ├── agent/              # LangGraph, nodes, prompts, state, Groq wrapper
│   │   ├── routers/            # FastAPI complaint routes
│   │   ├── services/           # Processing, documents, seed data, signals
│   │   ├── config.py           # Environment-backed settings
│   │   ├── crud.py             # Queries, mutations, status and audit logic
│   │   ├── database.py         # SQLAlchemy engine and sessions
│   │   ├── main.py             # FastAPI application entry point
│   │   ├── models.py           # Complaint and AuditEvent ORM models
│   │   ├── regulatory.py       # Deterministic due-date calculations
│   │   └── schemas.py          # API request and response models
│   ├── alembic/                # Database migrations
│   ├── sample_data/            # Demo PDF, email, and text complaints
│   └── tests/                  # Agent, API, regulatory, and signal tests
├── frontend/
│   ├── src/
│   │   ├── api/                # Axios client and processing polling
│   │   ├── components/         # Dashboard and workflow components
│   │   ├── pages/              # Dashboard and complaint details
│   │   └── store/              # Redux state and async actions
│   ├── Dockerfile
│   └── nginx.conf
└── docker-compose.yml
```

## Local setup

### Prerequisites

- Python 3.12+
- Node.js 20+ and npm
- A Groq API key for LLM mode (optional)
- Docker Desktop only if using PostgreSQL or the containerised stack

### 1. Clone the repository

```bash
git clone git@github.com:PriyanshuGeTRekT/AIVOA-Full-Stack-Developer-Assessment.git
cd AIVOA-Full-Stack-Developer-Assessment
```

### 2. Start the backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS/Linux
source .venv/bin/activate
```

Install dependencies and create the local environment file:

```bash
pip install -r requirements.txt
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS/Linux
cp .env.example .env
```

To enable Groq, edit `backend/.env`:

```dotenv
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
GROQ_FALLBACK_MODEL=openai/gpt-oss-20b
```

Never commit `.env`; it is excluded by `.gitignore`.

Start FastAPI:

```bash
uvicorn app.main:app --reload --port 8000
```

- API: [http://localhost:8000](http://localhost:8000)
- Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health and active LLM mode: [http://localhost:8000/api/health](http://localhost:8000/api/health)

On first boot, SQLite tables are created and sample complaints are seeded.

### 3. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). During development, Vite proxies `/api` requests to FastAPI on port `8000`.

## Docker and PostgreSQL

Start only PostgreSQL:

```bash
docker compose up -d db
```

Then set this in `backend/.env`:

```dotenv
DATABASE_URL=postgresql+psycopg2://qms:qms@localhost:5432/complaints
```

Apply migrations:

```bash
cd backend
alembic upgrade head
```

Start the complete containerised stack:

```bash
docker compose --profile full up --build
```

The frontend is exposed on port `5173`, the API on `8000`, and PostgreSQL on `5432`.

## Frontend workflow

1. Review dashboard statistics and detected quality signals.
2. Select **New Complaint**.
3. Paste complaint text or upload a file from `backend/sample_data`.
4. Submit and wait while the UI polls `processing_state`.
5. Open the generated complaint to inspect extraction, completeness, risk, reportability, related records, RCA, CAPA, and audit history.
6. Move the complaint from `open` to `under_review` and then `closed`.
7. If needed, override AI risk with a reviewer name and reason.
8. Use **Re-run AI** after correcting or reviewing the source information.

Supported uploads include PDF, TXT, EML, Markdown, CSV, and common image extensions. Image OCR is not implemented; image-only uploads require an extraction integration before they can produce complaint text.

## API summary

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Database health, processing mode, and LLM mode |
| `GET` | `/api/stats` | Dashboard counters |
| `GET` | `/api/signals` | Batch and product/defect trend signals |
| `GET` | `/api/complaints` | Filtered, searched, sorted, paginated worklist |
| `GET` | `/api/complaints/{id}` | Complete complaint record and audit history |
| `GET` | `/api/complaints/{id}/related` | Complaints related by batch |
| `POST` | `/api/complaints` | Create a complaint from text |
| `POST` | `/api/complaints/upload` | Create a complaint from an uploaded file |
| `PATCH` | `/api/complaints/{id}/status` | Apply a valid status transition |
| `PATCH` | `/api/complaints/{id}/risk` | Apply a human risk override |
| `POST` | `/api/complaints/{id}/reprocess` | Re-run the LangGraph workflow |

## Tests and CI

Run the backend tests:

```bash
cd backend
pytest -q
```

Build the frontend:

```bash
cd frontend
npm run build
```

GitHub Actions runs both checks for pushes to `main`/`master` and for pull requests. Tests use in-memory SQLite, synchronous processing, and heuristic mode so CI does not require secrets.

## Key design decisions

- **Hybrid AI and deterministic processing:** language models handle interpretation and drafting; repeatable business rules handle duplicates, deadlines, workflow transitions, and trend thresholds.
- **Graceful model fallback:** each LLM node can continue with heuristics if credentials, network access, model availability, or JSON output fails.
- **Human authority over AI:** QA can override risk, but the original AI value and audit trail remain available.
- **Background processing:** complaint creation returns promptly while the frontend polls a clear processing state.
- **Conditional graph routing:** strong duplicates skip unnecessary RCA and CAPA generation.
- **Portable persistence:** SQLite enables zero-setup evaluation; PostgreSQL and Alembic provide a production-style path.
- **Explainability:** rationales, completeness results, duplicate scores, report reasons, deadlines, and audit events are visible instead of hiding decisions behind one model response.

## Important limitations

- AI recommendations are drafts for qualified human review, not final regulatory or medical decisions.
- Regulatory windows in `regulatory.py` are demonstration defaults and must be replaced with approved site SOPs and jurisdiction-specific requirements.
- The application has no authentication or role-based access control.
- Uploaded files are parsed in memory; production deployments should add malware scanning and managed object storage.
- Duplicate detection is lexical rather than embedding-based.
- Image OCR is not currently implemented.
