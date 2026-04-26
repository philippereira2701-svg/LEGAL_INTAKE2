"""phase2 sla mercury

Revision ID: 005_phase2_sla_mercury
Revises: 004_foundation_outbox_timeline
Create Date: 2026-04-26 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "005_phase2_sla_mercury"
down_revision = "004_foundation_outbox_timeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("lead_received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("leads", sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leads", sa.Column("first_human_contact_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leads", sa.Column("appointment_booked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leads", sa.Column("retained_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "mercury_escalations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("owner_phone", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalation_key", sa.String(length=120), nullable=False, unique=True),
    )
    op.create_index("idx_mercury_escalations_tenant", "mercury_escalations", ["tenant_id"], unique=False)
    op.create_index("idx_mercury_escalations_lead", "mercury_escalations", ["lead_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_mercury_escalations_lead", table_name="mercury_escalations")
    op.drop_index("idx_mercury_escalations_tenant", table_name="mercury_escalations")
    op.drop_table("mercury_escalations")
    op.drop_column("leads", "retained_at")
    op.drop_column("leads", "appointment_booked_at")
    op.drop_column("leads", "first_human_contact_at")
    op.drop_column("leads", "first_response_at")
    op.drop_column("leads", "lead_received_at")
