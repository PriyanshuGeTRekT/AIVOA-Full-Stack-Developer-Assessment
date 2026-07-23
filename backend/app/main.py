"""FastAPI application entry point.

Wires together the database, CORS for the React dev server, the complaint
routes and a one time seed so the app is usable the moment it boots.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import complaints
from app.services.seed import seed_if_empty

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables and seed on startup. For a real deployment we would use
    # Alembic migrations instead of create_all, but this keeps the demo one
    # command to run.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_if_empty(db)

    mode = "Groq" if settings.has_groq else "heuristic fallback (no GROQ_API_KEY)"
    logger.info("%s started. LLM mode: %s", settings.app_name, mode)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(complaints.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "llm_mode": "groq" if settings.has_groq else "heuristic"}
