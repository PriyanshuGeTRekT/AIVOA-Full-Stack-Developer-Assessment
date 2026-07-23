"""DB helpers used by routers (queries, creates, status/risk updates)."""

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import regulatory
from app.models import AuditEvent, Complaint

STATUS_TRANSITIONS = {
    "open": {"under_review", "closed"},
    "under_review": {"open", "closed"},
    "closed": {"under_review"},
}


class InvalidStatusTransition(ValueError):
    pass


def next_reference(db: Session) -> str:
    """Next CMP-YYYY-NNNN for the current year (max suffix + 1)."""
    year = datetime.now(timezone.utc).year
    prefix = f"CMP-{year}-"
    stmt = select(Complaint.reference).where(Complaint.reference.like(f"{prefix}%"))
    max_n = 0
    for ref in db.scalars(stmt):
        try:
            max_n = max(max_n, int(str(ref).rsplit("-", 1)[-1]))
        except (TypeError, ValueError):
            continue
    return f"{prefix}{max_n + 1:04d}"


def create_complaint(
    db: Session,
    source_text: str,
    channel: str = "manual",
    original_filename: str | None = None,
    *,
    max_attempts: int = 5,
) -> Complaint:
    """Insert a complaint; retry if reference collides under concurrent writers."""
    last_error: Exception | None = None
    for _ in range(max_attempts):
        complaint = Complaint(
            reference=next_reference(db),
            channel=channel,
            source_text=source_text,
            original_filename=original_filename,
            processing_state="pending",
        )
        db.add(complaint)
        try:
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
        except IntegrityError as exc:
            db.rollback()
            last_error = exc
            continue
    raise RuntimeError("Could not allocate a unique complaint reference") from last_error


def get_complaint(db: Session, complaint_id: int) -> Complaint | None:
    return db.get(Complaint, complaint_id)


def get_complaint_by_reference(db: Session, reference: str) -> Complaint | None:
    return db.scalar(select(Complaint).where(Complaint.reference == reference))


def list_complaints(
    db: Session,
    *,
    status: str | None = None,
    risk_level: str | None = None,
    reportable: bool | None = None,
    overdue: bool | None = None,
    processing_state: str | None = None,
    q: str | None = None,
    sort: str = "created_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Complaint], int]:
    """Filtered/sorted page of complaints and total count."""
    stmt = select(Complaint)
    count_stmt = select(func.count()).select_from(Complaint)
    now = datetime.now(timezone.utc)

    conditions = []
    if status:
        conditions.append(Complaint.status == status)
    if risk_level:
        conditions.append(Complaint.risk_level == risk_level)
    if reportable is not None:
        conditions.append(Complaint.reportable.is_(reportable))
    if processing_state:
        conditions.append(Complaint.processing_state == processing_state)
    if overdue is True:
        conditions.extend(
            [
                Complaint.status != "closed",
                Complaint.investigation_due_at.isnot(None),
                Complaint.investigation_due_at < now,
            ]
        )
    elif overdue is False:
        conditions.append(
            or_(
                Complaint.status == "closed",
                Complaint.investigation_due_at.is_(None),
                Complaint.investigation_due_at >= now,
            )
        )
    if q:
        like = f"%{q.strip()}%"
        conditions.append(
            or_(
                Complaint.reference.ilike(like),
                Complaint.product_name.ilike(like),
                Complaint.batch_number.ilike(like),
                Complaint.complaint_type.ilike(like),
                Complaint.description.ilike(like),
            )
        )

    for condition in conditions:
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    sort_map = {
        "created_at": Complaint.created_at,
        "reference": Complaint.reference,
        "risk_level": Complaint.risk_level,
        "status": Complaint.status,
        "product_name": Complaint.product_name,
    }
    sort_col = sort_map.get(sort, Complaint.created_at)
    stmt = stmt.order_by(sort_col.asc() if order == "asc" else sort_col.desc())

    page = max(1, page)
    page_size = min(max(1, page_size), 200)
    total = db.scalar(count_stmt) or 0
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def existing_for_duplicate_check(db: Session, exclude_id: int) -> list[dict]:
    """Rows used by the duplicate detector (exclude current id)."""
    stmt = select(Complaint).where(
        Complaint.id != exclude_id,
        Complaint.processing_state == "done",
    )
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
    """Append an audit row. Caller commits."""
    event = AuditEvent(complaint_id=complaint_id, actor=actor, action=action, detail=detail)
    db.add(event)
    return event


def update_status(
    db: Session,
    complaint: Complaint,
    status: str,
    actor: str = "QA Reviewer",
) -> Complaint:
    previous = complaint.status
    if previous == status:
        return complaint
    allowed = STATUS_TRANSITIONS.get(previous, set())
    if status not in allowed:
        raise InvalidStatusTransition(
            f"Cannot move from '{previous}' to '{status}'. Allowed: {sorted(allowed) or 'none'}"
        )
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
    """QA overrides risk; keep original AI level and recompute investigation SLA."""
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
        "processing": count_where(
            Complaint.processing_state.in_(["pending", "processing"])
        ),
    }
