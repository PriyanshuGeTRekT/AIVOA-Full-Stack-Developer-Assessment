"""Pytest fixtures: in-memory SQLite + SYNC_PROCESSING for API tests."""

import os

# Must be set before app modules cache settings.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["GROQ_API_KEY"] = ""
os.environ["SYNC_PROCESSING"] = "true"
os.environ["ENVIRONMENT"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Clear settings cache after env is set.
from app.config import get_settings

get_settings.cache_clear()

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # Avoid seeding the shared app engine during tests.
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
