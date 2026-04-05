"""initial

Revision ID: 001
Revises: 
Create Date: 2026-03-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 1. Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # 2. Create tenants table
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('firm_name', sa.String(length=200), nullable=False),
        sa.Column('firm_slug', sa.String(length=100), nullable=False),
        sa.Column('lawyer_phone', sa.String(length=20), nullable=True),
        sa.Column('lawyer_email', sa.String(length=100), nullable=True),
        sa.Column('calendly_link', sa.String(length=300), nullable=True),
        sa.Column('twilio_account_sid', sa.String(length=60), nullable=True),
        sa.Column('twilio_auth_token', sa.String(length=255), nullable=True),
        sa.Column('twilio_from_number', sa.String(length=20), nullable=True),
        sa.Column('gemini_scoring_rubric', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('plan', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('monthly_lead_count', sa.Integer(), nullable=True),
        sa.Column('monthly_lead_limit', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('firm_slug')
    )

    # 3. Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=200), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # 4. Create leads table
    op.create_table('leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('client_name', sa.String(length=100), nullable=False),
        sa.Column('client_phone', sa.String(length=20), nullable=True),
        sa.Column('client_email', sa.String(length=100), nullable=True),
        sa.Column('incident_description', sa.Text(), nullable=True),
        sa.Column('police_report_filed', sa.Boolean(), nullable=True),
        sa.Column('medical_treatment_received', sa.Boolean(), nullable=True),
        sa.Column('hospitalized', sa.Boolean(), nullable=True),
        sa.Column('incident_date_raw', sa.String(length=100), nullable=True),
        sa.Column('incident_days_ago', sa.Integer(), nullable=True),
        sa.Column('already_represented', sa.Boolean(), nullable=True),
        sa.Column('estimated_medical_bills', sa.String(length=50), nullable=True),
        sa.Column('ai_score', sa.Integer(), nullable=True),
        sa.Column('rule_engine_score', sa.Integer(), nullable=True),
        sa.Column('final_score', sa.Integer(), nullable=True),
        sa.Column('ai_tier', sa.String(length=30), nullable=True),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('liability_score', sa.Integer(), nullable=True),
        sa.Column('damages_score', sa.Integer(), nullable=True),
        sa.Column('sol_score', sa.Integer(), nullable=True),
        sa.Column('red_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recommended_action', sa.String(length=30), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('injection_risk_detected', sa.Boolean(), nullable=True),
        sa.Column('raw_form_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint('ai_score >= 1 AND ai_score <= 10', name='check_ai_score_range'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_leads_created_at', 'leads', [sa.text('created_at DESC')], unique=False)
    op.create_index('idx_leads_final_score', 'leads', [sa.text('final_score DESC')], unique=False)
    op.create_index('idx_leads_status', 'leads', ['status'], unique=False)
    op.create_index('idx_leads_tenant_id', 'leads', ['tenant_id'], unique=False)

    # 5. Create lead_events table
    op.create_table('lead_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=True),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('performed_by', sa.String(length=50), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. Create communications table
    op.create_table('communications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('channel', sa.String(length=20), nullable=True),
        sa.Column('recipient', sa.String(length=100), nullable=True),
        sa.Column('recipient_type', sa.String(length=20), nullable=True),
        sa.Column('message_body', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('provider_message_id', sa.String(length=100), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=True),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 7. Apply RLS Policies
    op.execute("ALTER TABLE leads ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE lead_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE communications ENABLE ROW LEVEL SECURITY")
    
    op.execute("CREATE POLICY tenant_isolation_leads ON leads USING (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("CREATE POLICY tenant_isolation_events ON lead_events USING (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("CREATE POLICY tenant_isolation_comms ON communications USING (tenant_id = current_setting('app.tenant_id')::uuid)")

def downgrade():
    op.drop_table('communications')
    op.drop_table('lead_events')
    op.drop_table('leads')
    op.drop_table('users')
    op.drop_table('tenants')
