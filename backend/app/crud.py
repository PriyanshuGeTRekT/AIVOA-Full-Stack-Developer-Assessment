"""Database access helpers.

Routers call these functions rather than touching the session directly, so the
query logic lives in one place and stays easy to test.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import regulatory
from app.models import AuditEvent, Complaint


def next_reference(db: Session) -> str:
    """Generate a human friendly reference like CMP-2026-0007.

    We count existing rows for the current year and add one. This is fine for a
    single writer demo; a production system would use a dedicated sequence.
    """
    year = datetime.now(timezone.utc).year
    count = db.scalar(select(func.count()).select_from(Complaint)) or 0
    return f"CMP-{year}-{count + 1:04d}"


def create_complaint(
    db: Session,
    source_text: str,
    channel: str = "manual",
    original_filename: str | None = None,
) -> Complaint:
    complaint = Complaint(
        reference=next_reference(db),
        channel=channel,
        source_text=source_text,
        original_filename=original_filename,
        processing_state="pending",
    )
    db.add(complaint)
    db.flush()  # assign the id so the audit event can reference it
    add_audit(
        db,
        complaint.id,
        actor="System",
        action="Complaint received",
        detail=f"Logged via {channel} channel",
    )
    db.commit()
    db.refresh(complaint)
    return complaint


def get_complaint(db: Session, complaint_id: int) -> Complaint | None:
    return db.get(Complaint, complaint_id)


def list_complaints(db: Session) -> list[Complaint]:
    stmt = select(Complaint).order_by(Complaint.created_at.desc())
    return list(db.scalars(stmt))


def existing_for_duplicate_check(db: Session, exclude_id: int) -> list[dict]:
    """Return lightweight records the duplicate node compares against."""
    stmt = select(Complaint).where(Complaint.id != exclude_id)
    return [
        {
            "id": c.id,
            "reference": c.reference,
            "product_name": c.product_name,
            "batch_number": c.batch_number,
            "description": c.description or c.source_text,
        }
        for c in db.scalars(stmt)
    ]


def add_audit(
    db: Session,
    complaint_id: int,
    actor: str,
    action: str,
    detail: str | None = None,
) -> AuditEvent:
    """Record one entry in a complaint's audit trail. Caller owns the commit."""
    event = AuditEvent(complaint_id=complaint_id, actor=actor, action=action, detail=detail)
    db.add(event)
    return event


def update_status(db: Session, complaint: Complaint, status: str, actor: str = "QA Reviewer") -> Complaint:
    previous = complaint.status
    complaint.status = status
    add_audit(
        db,
        complaint.id,
        actor=actor,
        action="Status changed",
        detail=f"{previous} -> {status}",
    )
    db.commit()
    db.refresh(complaint)
    return complaint


def override_risk(
    db: Session,
    complaint: Complaint,
    new_risk: str,
    reason: str,
    actor: str = "QA Reviewer",
) -> Complaint:
    """Let a human QA reviewer overrule the AI risk level, with a recorded reason.

    In a regulated process the AI only advises; the human owns the decision. We
    keep the AI's original call on ai_risk_level and recompute the investigation
    deadline from the new level so the SLA stays consistent.
    """
    previous = complaint.risk_level
    complaint.risk_level = new_risk
    complaint.risk_overridden = True
    complaint.investigation_due_at = regulatory.investigation_due_date(
        new_risk, complaint.created_at
    )
    add_audit(
        db,
        complaint.id,
        actor=actor,
        action="Risk level overridden",
        detail=f"{previous} -> {new_risk}. Reason: {reason}",
    )
    db.commit()
    db.refresh(complaint)
    return complaint


def dashboard_stats(db: Session) -> dict:
    def count_where(*conditions) -> int:
        stmt = select(func.count()).select_from(Complaint)
        for condition in conditions:
            stmt = stmt.where(condition)
        return db.scalar(stmt) or 0

    now = datetime.now(timezone.utc)
    return {
        "total": count_where(),
        "open": count_where(Complaint.status == "open"),
        "under_review": count_where(Complaint.status == "under_review"),
        "closed": count_where(Complaint.status == "closed"),
        "critical": count_where(Complaint.risk_level == "Critical"),
        "major": count_where(Complaint.risk_level == "Major"),
        "minor": count_where(Complaint.risk_level == "Minor"),
        "reportable": count_where(Complaint.reportable.is_(True)),
        "overdue": count_where(
            Complaint.status != "closed",
            Complaint.investigation_due_at.isnot(None),
            Complaint.investigation_due_at < now,
        ),
    }
