"""HTTP routes for the complaint workflow.

The create and upload endpoints process the complaint through the agent before
returning, so the client gets the fully enriched record in one round trip. That
keeps the demo flow simple. For heavier production loads this is the natural
place to hand off to a background task and let the client poll processing_state.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import (
    ComplaintCreate,
    ComplaintRead,
    ComplaintSummaryRow,
    DashboardStats,
    QualitySignal,
    RelatedComplaints,
    RiskOverride,
    StatusUpdate,
)
from app.services import documents, signals
from app.services.processing import process_complaint

router = APIRouter(prefix="/api", tags=["complaints"])


@router.post("/complaints", response_model=ComplaintRead, status_code=201)
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db)):
    """Create a complaint from pasted text and run the agent on it."""
    complaint = crud.create_complaint(db, source_text=payload.source_text, channel=payload.channel)
    return process_complaint(db, complaint)


@router.post("/complaints/upload", response_model=ComplaintRead, status_code=201)
async def upload_complaint(
    file: UploadFile = File(...),
    channel: str = Form(default="upload"),
    db: Session = Depends(get_db),
):
    """Create a complaint from an uploaded PDF, email or text file."""
    content = await file.read()
    text = documents.extract_text(file.filename, content)
    if not text or len(text.strip()) < 5:
        raise HTTPException(status_code=422, detail="Could not read any text from the file.")

    complaint = crud.create_complaint(
        db, source_text=text, channel=channel, original_filename=file.filename
    )
    return process_complaint(db, complaint)


@router.get("/complaints", response_model=list[ComplaintSummaryRow])
def list_complaints(db: Session = Depends(get_db)):
    return crud.list_complaints(db)


@router.get("/complaints/{complaint_id}", response_model=ComplaintRead)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    complaint = crud.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@router.patch("/complaints/{complaint_id}/status", response_model=ComplaintRead)
def update_status(complaint_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    complaint = crud.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return crud.update_status(db, complaint, payload.status)


@router.patch("/complaints/{complaint_id}/risk", response_model=ComplaintRead)
def override_risk(complaint_id: int, payload: RiskOverride, db: Session = Depends(get_db)):
    """QA reviewer overrides the AI risk level. The AI call is kept for audit."""
    complaint = crud.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return crud.override_risk(db, complaint, payload.risk_level, payload.reason, payload.actor)


@router.get("/complaints/{complaint_id}/related", response_model=RelatedComplaints)
def related(complaint_id: int, db: Session = Depends(get_db)):
    complaint = crud.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return signals.related_complaints(db, complaint)


@router.post("/complaints/{complaint_id}/reprocess", response_model=ComplaintRead)
def reprocess(complaint_id: int, db: Session = Depends(get_db)):
    """Re-run the agent, handy after configuring a Groq key."""
    complaint = crud.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return process_complaint(db, complaint)


@router.get("/stats", response_model=DashboardStats)
def stats(db: Session = Depends(get_db)):
    return crud.dashboard_stats(db)


@router.get("/signals", response_model=list[QualitySignal])
def quality_signals(db: Session = Depends(get_db)):
    """Detected trends across complaints (batch clusters, recurring defects)."""
    return signals.detect_signals(db)
