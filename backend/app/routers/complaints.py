"""Complaint API routes. Create/upload enqueue AI processing unless SYNC_PROCESSING."""

import math
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app import crud
from app.config import get_settings
from app.crud import InvalidStatusTransition
from app.database import get_db
from app.schemas import (
    ComplaintCreate,
    ComplaintRead,
    DashboardStats,
    PaginatedComplaints,
    QualitySignal,
    RelatedComplaints,
    RiskOverride,
    StatusUpdate,
)
from app.services import documents, signals
from app.services.processing import process_complaint, process_complaint_by_id

router = APIRouter(prefix="/api", tags=["complaints"])
settings = get_settings()


def _enrich_read(db: Session, complaint) -> ComplaintRead:
    """Add duplicate_reference when duplicate_of is set."""
    data = ComplaintRead.model_validate(complaint)
    if complaint.duplicate_of:
        other = crud.get_complaint(db, complaint.duplicate_of)
        if other:
            data.duplicate_reference = other.reference
    return data


def _run_or_enqueue(background_tasks: BackgroundTasks, db: Session, complaint):
    if settings.sync_processing:
        return _enrich_read(db, process_complaint(db, complaint))
    background_tasks.add_task(process_complaint_by_id, complaint.id)
    db.refresh(complaint)
    return _enrich_read(db, complaint)


@router.post("/complaints", response_model=ComplaintRead, status_code=201)
def create_complaint(
    payload: ComplaintCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create from pasted text and start processing."""
    complaint = crud.create_complaint(db, source_text=payload.source_text, channel=payload.channel)
    return _run_or_enqueue(background_tasks, db, complaint)


@router.post("/complaints/upload", response_model=ComplaintRead, status_code=201)
async def upload_complaint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    channel: str = Form(default="upload"),
    db: Session = Depends(get_db),
):
    """Create from an uploaded file and start processing."""
    filename = file.filename or "upload.bin"
    suffix = Path(filename).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(settings.allowed_extensions)}",
        )

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB upload limit.",
        )

    try:
        text = documents.extract_text(filename, content)
    except documents.DocumentExtractError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not text or len(text.strip()) < 5:
        raise HTTPException(status_code=422, detail="Could not read any text from the file.")

    complaint = crud.create_complaint(
        db, source_text=text, channel=channel, original_filename=filename
    )
    return _run_or_enqueue(background_tasks, db, complaint)


@router.get("/complaints", response_model=PaginatedComplaints)
def list_complaints(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    reportable: bool | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    processing_state: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Search reference, product, batch, type"),
    sort: str = Query(default="created_at"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    rows, total = crud.list_complaints(
        db,
        status=status,
        risk_level=risk_level,
        reportable=reportable,
        overdue=overdue,
        processing_state=processing_state,
        q=q,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )
    pages = max(1, math.ceil(total / page_size)) if total else 1
    return PaginatedComplaints(
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/complaints/{complaint_id}", response_model=ComplaintRead)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    complaint = crud.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return _enrich_read(db, complaint)


@router.patch("/complaints/{complaint_id}/status", response_model=ComplaintRead)
def update_status(complaint_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    complaint = crud.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    try:
        updated = crud.update_status(db, complaint, payload.status)
    except InvalidStatusTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _enrich_read(db, updated)


@router.patch("/complaints/{complaint_id}/risk", response_model=ComplaintRead)
def override_risk(complaint_id: int, payload: RiskOverride, db: Session = Depends(get_db)):
    """Human override of AI risk (original AI level is retained)."""
    complaint = crud.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    updated = crud.override_risk(db, complaint, payload.risk_level, payload.reason, payload.actor)
    return _enrich_read(db, updated)


@router.get("/complaints/{complaint_id}/related", response_model=RelatedComplaints)
def related(complaint_id: int, db: Session = Depends(get_db)):
    complaint = crud.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return signals.related_complaints(db, complaint)


@router.post("/complaints/{complaint_id}/reprocess", response_model=ComplaintRead)
def reprocess(
    complaint_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Re-run the agent on an existing complaint."""
    complaint = crud.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    complaint.processing_state = "pending"
    complaint.processing_error = None
    db.commit()
    db.refresh(complaint)
    return _run_or_enqueue(background_tasks, db, complaint)


@router.get("/stats", response_model=DashboardStats)
def stats(db: Session = Depends(get_db)):
    return crud.dashboard_stats(db)


@router.get("/signals", response_model=list[QualitySignal])
def quality_signals(db: Session = Depends(get_db)):
    return signals.detect_signals(db)
