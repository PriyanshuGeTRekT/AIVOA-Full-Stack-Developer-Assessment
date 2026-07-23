"""ORM models: Complaint (intake + AI fields) and AuditEvent (change history)."""

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

    # e.g. CMP-2026-0007
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    channel: Mapped[str] = mapped_column(String(32), default="manual")
    source_text: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Filled by the agent after processing.
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    complainant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    complainant_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    complaint_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # risk_level can be overridden by QA; ai_risk_level keeps the model call.
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    ai_risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    risk_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_overridden: Mapped[bool] = mapped_column(Boolean, default=False)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    capa: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Category/reason from agent; due date from regulatory.py.
    reportable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    report_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    investigation_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    completeness: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # SET NULL if the original row is deleted later.
    duplicate_of: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("complaints.id", ondelete="SET NULL"), nullable=True
    )
    duplicate_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # open -> under_review -> closed
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)

    # pending | processing | done | failed
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

    @property
    def investigation_days_left(self) -> int | None:
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
    """One change history row for a complaint."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    actor: Mapped[str] = mapped_column(String(64), default="System")
    action: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    complaint: Mapped["Complaint"] = relationship(back_populates="audit_events")
