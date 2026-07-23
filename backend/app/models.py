"""SQLAlchemy ORM models.

The Complaint table stores both the raw intake and everything the AI agent
derives from it. Keeping the agent output on the same row keeps the read path
simple: one query gives the UI the full picture of a complaint. AuditEvent adds
the paper trail a regulated process needs: every meaningful change is recorded
with who did it and why.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.regulatory import days_until


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
    batch_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    complainant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    complainant_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    complaint_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI derived fields. ai_risk_level preserves the model's original call even
    # after a human overrides risk_level, so the audit story stays intact.
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    ai_risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    risk_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_overridden: Mapped[bool] = mapped_column(Boolean, default=False)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    capa: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Regulatory reportability. The agent decides the category and reason; the
    # deadline is computed deterministically from the received date.
    reportable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    report_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Internal investigation SLA driven by the risk level.
    investigation_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Completeness and duplicate detection results.
    completeness: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    duplicate_of: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duplicate_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Workflow status: open -> under_review -> closed.
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)

    # Processing lifecycle so the UI can show a spinner while the agent runs.
    processing_state: Mapped[str] = mapped_column(String(32), default="pending")
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="AuditEvent.created_at",
    )

    # --- Derived, read only helpers exposed to the API via from_attributes. ---
    @property
    def investigation_days_left(self) -> int | None:
        # Once closed the clock is not relevant, so we hide the countdown.
        if self.status == "closed":
            return None
        return days_until(self.investigation_due_at)

    @property
    def is_overdue(self) -> bool:
        left = self.investigation_days_left
        return left is not None and left < 0

    @property
    def report_days_left(self) -> int | None:
        return days_until(self.report_due_at)


class AuditEvent(Base):
    """A single entry in a complaint's history (GMP style audit trail)."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    actor: Mapped[str] = mapped_column(String(64), default="System")
    action: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    complaint: Mapped["Complaint"] = relationship(back_populates="audit_events")
