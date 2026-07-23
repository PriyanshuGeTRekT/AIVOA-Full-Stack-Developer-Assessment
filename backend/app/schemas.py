"""Pydantic schemas used at the API boundary.

These are intentionally separate from the ORM models. The API contract should
be free to differ from the storage layout, and it keeps request validation and
response shaping in one obvious place.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ComplaintCreate(BaseModel):
    """Payload for creating a complaint from pasted text."""

    source_text: str = Field(min_length=5, description="Raw complaint body")
    channel: str = Field(default="manual")


class CompletenessResult(BaseModel):
    is_complete: bool
    missing_fields: list[str] = Field(default_factory=list)
    notes: str | None = None


class ComplaintRead(BaseModel):
    """Full complaint as returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    channel: str
    source_text: str
    original_filename: str | None = None

    product_name: str | None = None
    batch_number: str | None = None
    complainant_name: str | None = None
    complainant_contact: str | None = None
    complaint_type: str | None = None
    description: str | None = None

    risk_level: str | None = None
    risk_rationale: str | None = None
    summary: str | None = None
    root_cause: str | None = None
    capa: str | None = None

    completeness: CompletenessResult | None = None
    duplicate_of: int | None = None
    duplicate_score: float | None = None

    status: str
    processing_state: str
    processing_error: str | None = None

    created_at: datetime
    updated_at: datetime


class ComplaintSummaryRow(BaseModel):
    """Lightweight row for the dashboard list view."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    product_name: str | None = None
    batch_number: str | None = None
    complaint_type: str | None = None
    risk_level: str | None = None
    status: str
    processing_state: str
    created_at: datetime


class StatusUpdate(BaseModel):
    status: str = Field(pattern="^(open|under_review|closed)$")


class DashboardStats(BaseModel):
    total: int
    open: int
    under_review: int
    closed: int
    critical: int
    major: int
    minor: int
