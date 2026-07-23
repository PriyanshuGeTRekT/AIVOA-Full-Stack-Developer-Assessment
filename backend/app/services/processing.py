"""Glue between the LangGraph agent and the database.

This is where a stored complaint gets handed to the graph and where the graph's
output is written back onto the row. Keeping it separate from the router means
we could later move it onto a background worker without touching the API.
"""

import logging

from sqlalchemy.orm import Session

from app import crud, regulatory
from app.agent.graph import run_pipeline
from app.models import Complaint

logger = logging.getLogger(__name__)


def process_complaint(db: Session, complaint: Complaint) -> Complaint:
    """Run the agent on a complaint and persist everything it produced."""
    complaint.processing_state = "processing"
    complaint.processing_error = None
    db.commit()

    existing = crud.existing_for_duplicate_check(db, exclude_id=complaint.id)

    try:
        result = run_pipeline(complaint.source_text, existing)
    except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
        logger.exception("Agent pipeline failed for complaint %s", complaint.reference)
        complaint.processing_state = "failed"
        complaint.processing_error = str(exc)
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

    complaint.risk_level = result.get("risk_level")
    # Only overwrite the AI baseline if a human has not taken control of it.
    if not complaint.risk_overridden:
        complaint.ai_risk_level = result.get("risk_level")
    complaint.risk_rationale = result.get("risk_rationale")
    complaint.summary = result.get("summary")
    complaint.root_cause = result.get("root_cause")
    complaint.capa = result.get("capa")
    complaint.completeness = result.get("completeness")
    complaint.duplicate_of = result.get("duplicate_of")
    complaint.duplicate_score = result.get("duplicate_score")

    # Regulatory reportability and its deadline.
    complaint.reportable = result.get("reportable")
    complaint.report_type = result.get("report_type")
    complaint.report_reason = result.get("report_reason")
    complaint.report_due_at = regulatory.report_due_date(
        complaint.report_type, complaint.created_at
    )

    # Investigation SLA follows the assessed risk level.
    complaint.investigation_due_at = regulatory.investigation_due_date(
        complaint.risk_level, complaint.created_at
    )

    complaint.processing_state = "done"

    detail = (
        f"Risk: {complaint.risk_level}; "
        f"Reportable: {complaint.report_type if complaint.reportable else 'No'}"
    )
    crud.add_audit(db, complaint.id, actor="AI Agent", action="AI analysis completed", detail=detail)

    db.commit()
    db.refresh(complaint)
    return complaint
