"""FastAPI entrypoint: DB setup, CORS, routes, optional seed data."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import complaints
from app.services.seed import seed_if_empty

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Demo-friendly: create tables on boot. Prefer `alembic upgrade head` in real deploys.
    Base.metadata.create_all(bind=engine)

    if settings.environment != "test":
        with SessionLocal() as db:
            seed_if_empty(db)

    mode = "Groq" if settings.has_groq else "heuristic fallback (no GROQ_API_KEY)"
    logger.info("%s started. LLM mode: %s", settings.app_name, mode)
    yield


app = FastAPI(title=settings.app_name, version="1.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(complaints.router)


@app.get("/api/health", tags=["health"])
def health():
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health DB check failed: %s", exc)

    return {
        "status": "ok" if db_ok else "degraded",
        "llm_mode": "groq" if settings.has_groq else "heuristic",
        "database": "up" if db_ok else "down",
        "sync_processing": settings.sync_processing,
    }
