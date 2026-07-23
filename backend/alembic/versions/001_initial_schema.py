"""Initial schema for complaints and audit events.

Revision ID: 001_initial
Revises:
Create Date: 2026-07-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "complaints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(length=32), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("batch_number", sa.String(length=128), nullable=True),
        sa.Column("complainant_name", sa.String(length=255), nullable=True),
        sa.Column("complainant_contact", sa.String(length=255), nullable=True),
        sa.Column("complaint_type", sa.String(length=128), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=True),
        sa.Column("ai_risk_level", sa.String(length=16), nullable=True),
        sa.Column("risk_rationale", sa.Text(), nullable=True),
        sa.Column("risk_overridden", sa.Boolean(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("capa", sa.Text(), nullable=True),
        sa.Column("reportable", sa.Boolean(), nullable=True),
        sa.Column("report_type", sa.String(length=64), nullable=True),
        sa.Column("report_reason", sa.Text(), nullable=True),
        sa.Column("report_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("investigation_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completeness", sa.JSON(), nullable=True),
        sa.Column("duplicate_of", sa.Integer(), nullable=True),
        sa.Column("duplicate_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("processing_state", sa.String(length=32), nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["duplicate_of"], ["complaints.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index("ix_complaints_reference", "complaints", ["reference"])
    op.create_index("ix_complaints_batch_number", "complaints", ["batch_number"])
    op.create_index("ix_complaints_risk_level", "complaints", ["risk_level"])
    op.create_index("ix_complaints_status", "complaints", ["status"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("complaint_id", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_complaint_id", "audit_events", ["complaint_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_complaint_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_complaints_status", table_name="complaints")
    op.drop_index("ix_complaints_risk_level", table_name="complaints")
    op.drop_index("ix_complaints_batch_number", table_name="complaints")
    op.drop_index("ix_complaints_reference", table_name="complaints")
    op.drop_table("complaints")
