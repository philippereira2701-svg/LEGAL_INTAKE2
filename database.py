import os
import uuid
import logging
import time
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from functools import wraps
from dotenv import load_dotenv
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, ForeignKey, 
    DateTime, Index, CheckConstraint, create_engine, text, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.exc import OperationalError

# Load environment variables from .env
load_dotenv()

# Production-grade Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DB_MANAGER")

DATABASE_URL = os.getenv("DATABASE_URL")

# --- AUTO-FALLBACK FOR TESTING ---
if not DATABASE_URL or "user:password@localhost" in DATABASE_URL:
    DATABASE_URL = "sqlite:///./test_legal_intake.db"
    logger.warning("PostgreSQL not configured. Falling back to SQLite for local testing: test_legal_intake.db")

Base = declarative_base()

# --- Models ---

class Tenant(Base):
    """Law firm multi-tenant record"""
    __tablename__ = 'tenants'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    firm_name = Column(String(200), nullable=False)
    firm_slug = Column(String(100), unique=True, nullable=False)
    lawyer_phone = Column(String(20))
    lawyer_email = Column(String(100))
    is_active = Column(Boolean, default=True)

class Lead(Base):
    """Core intake record"""
    __tablename__ = 'leads'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    client_name = Column(String(100), nullable=False)
    client_phone = Column(String(20))
    client_email = Column(String(100))
    incident_description = Column(Text)
    incident_location = Column(String(200))
    incident_date = Column(String(100))
    injuries_sustained = Column(Text)
    police_report_filed = Column(Boolean, default=False)
    medical_treatment_received = Column(Boolean, default=False)
    ai_score = Column(Integer)
    ai_tier = Column(String(30))
    ai_summary = Column(Text)
    liability_score = Column(Integer)
    damages_score = Column(Integer)
    sol_score = Column(Integer)
    red_flags = Column(Text, default="[]") # JSON string for SQLite
    recommended_action = Column(String(30))
    status = Column(String(30), default='pending')
    action_taken = Column(String(100), default="None")

# --- Database Management ---

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class DatabaseManager:
    """Enhanced database controller with standalone support."""
    
    def __init__(self, session: Optional[Session] = None):
        self._provided_session = session
        Base.metadata.create_all(bind=engine)

    def get_session(self):
        if self._provided_session:
            return self._provided_session
        return SessionLocal()

    def seed_data(self):
        """Initializes default tenant for LEGAL_PRJ."""
        session = self.get_session()
        try:
            if not session.query(Tenant).filter_by(firm_slug="default").first():
                default_tenant = Tenant(
                    id="default-tenant-id",
                    firm_name="LEGAL_PRJ Global",
                    firm_slug="default",
                    lawyer_email="admin@legalprj.com"
                )
                session.add(default_tenant)
                session.commit()
                logger.info("SEED | Default Tenant Created")
        finally:
            if not self._provided_session: session.close()

    def insert_lead(self, lead_data: Dict[str, Any]) -> int:
        session = self.get_session()
        try:
            # Ensure we have a tenant
            tenant = session.query(Tenant).first()
            tid = tenant.id if tenant else None
            
            lead = Lead(tenant_id=tid, **lead_data)
            session.add(lead)
            session.commit()
            session.refresh(lead)
            return lead.id
        finally:
            if not self._provided_session: session.close()

    def get_dashboard_stats(self) -> Dict[str, Any]:
        session = self.get_session()
        try:
            total = session.query(func.count(Lead.id)).scalar() or 0
            avg_score = session.query(func.avg(Lead.ai_score)).scalar() or 0
            booked = session.query(func.count(Lead.id)).filter(Lead.ai_tier == 'BOOK NOW').scalar() or 0
            
            return {
                "total_leads": total,
                "avg_score": round(float(avg_score), 1),
                "book_now_count": booked,
                "conversion_rate": round((booked / total * 100), 1) if total > 0 else 0
            }
        finally:
            if not self._provided_session: session.close()

    def get_all_leads(self) -> List[Lead]:
        session = self.get_session()
        try:
            return session.query(Lead).order_by(Lead.created_at.desc()).all()
        finally:
            if not self._provided_session: session.close()

    def update_lead_action(self, lead_id: int, action: str):
        session = self.get_session()
        try:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                lead.action_taken = action
                session.commit()
        finally:
            if not self._provided_session: session.close()
