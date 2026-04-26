"""initial baseline schema aligned with runtime models.

Revision ID: 001
Revises:
Create Date: 2026-03-31 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("firm_name", sa.String(length=200), nullable=False),
        sa.Column("firm_slug", sa.String(length=100), nullable=False),
        sa.Column("calendly_link", sa.String(length=500), nullable=True),
        sa.Column("twilio_sid", sa.Text(), nullable=True),
        sa.Column("twilio_token", sa.Text(), nullable=True),
        sa.Column("twilio_phone", sa.Text(), nullable=True),
        sa.Column("gmail_address", sa.Text(), nullable=True),
        sa.Column("gmail_app_password", sa.Text(), nullable=True),
        sa.Column("lawyer_email", sa.Text(), nullable=True),
        sa.Column("lawyer_phone", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("firm_slug"),
    )
    op.create_index("ix_tenants_firm_slug", "tenants", ["firm_slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False, server_default="lawyer"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("action_taken", sa.String(length=80), nullable=False, server_default="QUEUED"),
        sa.Column("ai_score", sa.Integer(), nullable=True),
        sa.Column("ai_tier", sa.String(length=40), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("estimated_case_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("liability_score", sa.Integer(), nullable=True),
        sa.Column("damages_score", sa.Integer(), nullable=True),
        sa.Column("sol_score", sa.Integer(), nullable=True),
        sa.Column("red_flags", sa.JSON(), nullable=True),
        sa.Column("recommended_action", sa.String(length=40), nullable=True),
        sa.Column("client_name", sa.Text(), nullable=False),
        sa.Column("client_phone", sa.Text(), nullable=True),
        sa.Column("client_email", sa.Text(), nullable=True),
        sa.Column("incident_description", sa.Text(), nullable=True),
        sa.Column("incident_location", sa.Text(), nullable=True),
        sa.Column("incident_date", sa.String(length=100), nullable=True),
        sa.Column("injuries_sustained", sa.Text(), nullable=True),
        sa.Column("police_report_filed", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("medical_treatment_received", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_leads_tenant_id", "leads", ["tenant_id"], unique=False)

    op.create_table(
        "error_logs",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=True),
        sa.Column("context", sa.String(length=120), nullable=False),
        sa.Column("error_type", sa.String(length=120), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("error_logs")
    op.drop_table("leads")
    op.drop_table("users")
    op.drop_index("ix_tenants_firm_slug", table_name="tenants")
    op.drop_table("tenants")
