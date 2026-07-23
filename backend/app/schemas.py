"""Request/response schemas (API layer, separate from ORM)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ComplaintCreate(BaseModel):
    source_text: str = Field(min_length=5, description="Raw complaint body")
    channel: str = Field(default="manual")


class CompletenessResult(BaseModel):
    is_complete: bool
    missing_fields: list[str] = Field(default_factory=list)
    notes: str | None = None


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    actor: str
    action: str
    detail: str | None = None
    created_at: datetime


class ComplaintRead(BaseModel):
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
    ai_risk_level: str | None = None
    risk_overridden: bool = False
    risk_rationale: str | None = None
    summary: str | None = None
    root_cause: str | None = None
    capa: str | None = None

    reportable: bool | None = None
    report_type: str | None = None
    report_reason: str | None = None
    report_due_at: datetime | None = None
    report_days_left: int | None = None

    investigation_due_at: datetime | None = None
    investigation_days_left: int | None = None
    is_overdue: bool = False

    completeness: CompletenessResult | None = None
    duplicate_of: int | None = None
    duplicate_score: float | None = None
    duplicate_reference: str | None = None

    status: str
    processing_state: str
    processing_error: str | None = None

    created_at: datetime
    updated_at: datetime

    audit_events: list[AuditEventRead] = Field(default_factory=list)


class ComplaintSummaryRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    product_name: str | None = None
    batch_number: str | None = None
    complaint_type: str | None = None
    risk_level: str | None = None
    reportable: bool | None = None
    status: str
    processing_state: str
    investigation_days_left: int | None = None
    is_overdue: bool = False
    created_at: datetime


class PaginatedComplaints(BaseModel):
    items: list[ComplaintSummaryRow]
    total: int
    page: int
    page_size: int
    pages: int


class StatusUpdate(BaseModel):
    status: str = Field(pattern="^(open|under_review|closed)$")


class RiskOverride(BaseModel):
    risk_level: str = Field(pattern="^(Critical|Major|Minor)$")
    reason: str = Field(min_length=3, description="Why the AI decision is being changed")
    actor: str = Field(default="QA Reviewer")


class DashboardStats(BaseModel):
    total: int
    open: int
    under_review: int
    closed: int
    critical: int
    major: int
    minor: int
    reportable: int
    overdue: int
    processing: int = 0


class QualitySignal(BaseModel):
    kind: str
    label: str
    count: int
    severity: str | None = None
    product_name: str | None = None
    batch_number: str | None = None
    complaint_type: str | None = None
    references: list[str] = Field(default_factory=list)
    complaint_ids: list[int] = Field(default_factory=list)
    recommendation: str


class RelatedReference(BaseModel):
    id: int
    reference: str
    risk_level: str | None = None


class RelatedComplaints(BaseModel):
    batch_number: str | None = None
    count: int
    references: list[RelatedReference] = Field(default_factory=list)
