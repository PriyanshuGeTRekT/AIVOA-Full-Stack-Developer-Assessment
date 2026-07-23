"""SQLAlchemy ORM models.

The Complaint table stores both the raw intake and everything the AI agent
derives from it. Keeping the agent output on the same row keeps the read path
simple: one query gives the UI the full picture of a complaint.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Human readable reference, for example CMP-2026-0007.
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    # Raw intake. source_text is whatever we managed to read from the upload or
    # the pasted body; channel records how it arrived.
    channel: Mapped[str] = mapped_column(String(32), default="manual")
    source_text: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Structured fields extracted by the agent. They start empty and are filled
    # once the graph runs.
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    complainant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    complainant_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    complaint_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI derived fields.
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    risk_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    capa: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Completeness and duplicate detection results are small structured blobs,
    # so JSON keeps them together without extra tables.
    completeness: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    duplicate_of: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duplicate_score: Mapped[float | None] = mapped_column(nullable=True)

    # Workflow status: open -> under_review -> closed.
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)

    # Processing lifecycle so the UI can show a spinner while the agent runs.
    processing_state: Mapped[str] = mapped_column(String(32), default="pending")
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
