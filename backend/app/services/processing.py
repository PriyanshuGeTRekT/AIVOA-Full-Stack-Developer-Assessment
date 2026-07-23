"""Run the agent graph and write results onto a Complaint row."""

import logging

from sqlalchemy.orm import Session

from app import crud, regulatory
from app.agent.graph import run_pipeline
from app.database import SessionLocal
from app.models import Complaint

logger = logging.getLogger(__name__)


def process_complaint_by_id(complaint_id: int) -> None:
    """Background entry: own a session, process one complaint by id."""
    db = SessionLocal()
    try:
        complaint = crud.get_complaint(db, complaint_id)
        if complaint is None:
            logger.warning("Cannot process missing complaint id=%s", complaint_id)
            return
        process_complaint(db, complaint)
    except Exception:
        logger.exception("Background processing failed for complaint id=%s", complaint_id)
    finally:
        db.close()


def process_complaint(db: Session, complaint: Complaint) -> Complaint:
    """Run the agent and persist its outputs."""
    complaint.processing_state = "processing"
    complaint.processing_error = None
    db.commit()

    existing = crud.existing_for_duplicate_check(db, exclude_id=complaint.id)

    try:
        result = run_pipeline(complaint.source_text, existing)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent pipeline failed for complaint %s", complaint.reference)
        complaint.processing_state = "failed"
        complaint.processing_error = str(exc)
        crud.add_audit(
            db,
            complaint.id,
            actor="AI Agent",
            action="AI analysis failed",
            detail=str(exc),
        )
        db.commit()
        db.refresh(complaint)
        return complaint

    extracted = result.get("extracted", {})
    complaint.product_name = extracted.get("product_name")
    complaint.batch_number = extracted.get("batch_number")
    complaint.complainant_name = extracted.get("complainant_name")
    complaint.complainant_contact = extracted.get("complainant_contact")
    complaint.complaint_type = extracted.get("complaint_type")
    complaint.description = extracted.get("description")

    ai_risk = result.get("risk_level")
    # Keep QA override; only refresh the AI baseline field.
    if complaint.risk_overridden:
        complaint.ai_risk_level = ai_risk
        # risk_level and investigation SLA stay as the human set them.
        crud.add_audit(
            db,
            complaint.id,
            actor="AI Agent",
            action="AI re-analysis completed (human risk retained)",
            detail=f"AI risk would be {ai_risk}; human override kept at {complaint.risk_level}",
        )
    else:
        complaint.risk_level = ai_risk
        complaint.ai_risk_level = ai_risk
        complaint.investigation_due_at = regulatory.investigation_due_date(
            complaint.risk_level, complaint.created_at
        )

    complaint.risk_rationale = result.get("risk_rationale")
    complaint.summary = result.get("summary")
    complaint.root_cause = result.get("root_cause")
    complaint.capa = result.get("capa")
    complaint.completeness = result.get("completeness")
    complaint.duplicate_of = result.get("duplicate_of")
    complaint.duplicate_score = result.get("duplicate_score")

    complaint.reportable = result.get("reportable")
    complaint.report_type = result.get("report_type")
    complaint.report_reason = result.get("report_reason")
    complaint.report_due_at = regulatory.report_due_date(
        complaint.report_type, complaint.created_at
    )

    if not complaint.risk_overridden:
        complaint.investigation_due_at = regulatory.investigation_due_date(
            complaint.risk_level, complaint.created_at
        )

    complaint.processing_state = "done"

    if not complaint.risk_overridden:
        detail = (
            f"Risk: {complaint.risk_level}; "
            f"Reportable: {complaint.report_type if complaint.reportable else 'No'}"
        )
        crud.add_audit(db, complaint.id, actor="AI Agent", action="AI analysis completed", detail=detail)

    db.commit()
    db.refresh(complaint)
    return complaint
