"""mercury policy ladder

Revision ID: 006_mercury_policy_ladder
Revises: 005_phase2_sla_mercury
Create Date: 2026-04-26 14:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "006_mercury_policy_ladder"
down_revision = "005_phase2_sla_mercury"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mercury_escalation_policies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("contacts", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("max_levels", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("parallel", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "idx_mercury_escalation_policies_tenant",
        "mercury_escalation_policies",
        ["tenant_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_mercury_escalation_policies_tenant", table_name="mercury_escalation_policies")
    op.drop_table("mercury_escalation_policies")
