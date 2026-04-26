"""foundation outbox timeline

Revision ID: 004_foundation_outbox_timeline
Revises: 001
Create Date: 2026-04-26 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "004_foundation_outbox_timeline"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS lead_events (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
            event_type VARCHAR(80) NOT NULL,
            event_payload JSON NOT NULL DEFAULT '{}'::json,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_lead_events_tenant_id ON lead_events(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_lead_events_lead_id ON lead_events(lead_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS communication_attempts (
            id SERIAL PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
            channel VARCHAR(20) NOT NULL,
            provider VARCHAR(40) NOT NULL,
            payload_snapshot JSON NOT NULL DEFAULT '{}'::json,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            provider_response_id VARCHAR(255),
            retry_count INTEGER NOT NULL DEFAULT 0,
            next_retry_at TIMESTAMPTZ,
            failure_reason TEXT,
            idempotency_key VARCHAR(120) NOT NULL UNIQUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_communication_attempts_tenant_id ON communication_attempts(tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_communication_attempts_status_next_retry ON communication_attempts(status, next_retry_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS communication_attempts")
    op.execute("DROP TABLE IF EXISTS lead_events")
