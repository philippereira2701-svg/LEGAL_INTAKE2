import base64
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
from sqlalchemy.types import TypeDecorator

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required.")
if not DATABASE_URL.startswith("postgresql"):
    raise RuntimeError("DATABASE_URL must point to PostgreSQL.")

_pii_key = os.getenv("PII_ENCRYPTION_KEY")
if not _pii_key:
    _pii_key = base64.urlsafe_b64encode(
        os.getenv("FLASK_SECRET_KEY", "intakeos-dev-key").encode().ljust(32, b"0")
    )
FERNET = Fernet(_pii_key)

Base = declarative_base()
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class EncryptedText(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        if value in (None, ""):
            return value
        return FERNET.encrypt(value.encode("utf-8")).decode("utf-8")

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        if value in (None, ""):
            return value
        try:
            return FERNET.decrypt(value.encode("utf-8")).decode("utf-8")
        except Exception:
            return value


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    firm_name = Column(String(200), nullable=False)
    firm_slug = Column(String(100), unique=True, nullable=False, index=True)
    calendly_link = Column(String(500))
    twilio_sid = Column(EncryptedText)
    twilio_token = Column(EncryptedText)
    twilio_phone = Column(EncryptedText)
    gmail_address = Column(EncryptedText)
    gmail_app_password = Column(EncryptedText)
    lawyer_email = Column(EncryptedText)
    lawyer_phone = Column(EncryptedText)
    is_active = Column(Boolean, default=True, nullable=False)

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(40), default="lawyer", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="users")


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(40), default="pending", nullable=False)
    action_taken = Column(String(80), default="QUEUED", nullable=False)
    ai_score = Column(Integer)
    ai_tier = Column(String(40))
    ai_summary = Column(Text)
    estimated_case_value = Column(Numeric(12, 2))
    liability_score = Column(Integer)
    damages_score = Column(Integer)
    sol_score = Column(Integer)
    red_flags = Column(JSON, default=list)
    recommended_action = Column(String(40))

    client_name = Column(EncryptedText, nullable=False)
    client_phone = Column(EncryptedText)
    client_email = Column(EncryptedText)
    incident_description = Column(EncryptedText)
    incident_location = Column(EncryptedText)
    incident_date = Column(String(100))
    injuries_sustained = Column(EncryptedText)
    police_report_filed = Column(Boolean, default=False)
    medical_treatment_received = Column(Boolean, default=False)
    lead_received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    first_response_at = Column(DateTime(timezone=True), nullable=True)
    first_human_contact_at = Column(DateTime(timezone=True), nullable=True)
    appointment_booked_at = Column(DateTime(timezone=True), nullable=True)
    retained_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", back_populates="leads")


class LeadEvent(Base):
    __tablename__ = "lead_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(80), nullable=False)
    event_payload = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CommunicationAttempt(Base):
    __tablename__ = "communication_attempts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(20), nullable=False)
    provider = Column(String(40), nullable=False)
    payload_snapshot = Column(JSON, default=dict, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    provider_response_id = Column(String(255))
    retry_count = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text)
    idempotency_key = Column(String(120), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MercuryEscalation(Base):
    __tablename__ = "mercury_escalations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(Integer, nullable=False, default=1)
    owner_phone = Column(EncryptedText, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    escalation_key = Column(String(120), unique=True, nullable=False, index=True)


class MercuryEscalationPolicy(Base):
    __tablename__ = "mercury_escalation_policies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    contacts = Column(JSON, nullable=False, default=list)
    timeout_seconds = Column(Integer, nullable=False, default=120)
    max_levels = Column(Integer, nullable=False, default=3)
    parallel = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ErrorLog(Base):
    __tablename__ = "error_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    context = Column(String(120), nullable=False)
    error_type = Column(String(120), nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DatabaseManager:
    def __init__(self, session: Optional[Session] = None, tenant_id: Optional[str] = None):
        self._provided_session = session
        self.tenant_id = tenant_id
        Base.metadata.create_all(bind=engine)

    def get_session(self) -> Session:
        if self._provided_session:
            return self._provided_session
        return SessionLocal()

    def create_tenant(self, tenant_data: Dict[str, Any]) -> Tenant:
        session = self.get_session()
        try:
            tenant = Tenant(**tenant_data)
            session.add(tenant)
            session.commit()
            session.refresh(tenant)
            return tenant
        finally:
            if not self._provided_session:
                session.close()

    def create_user(self, user_data: Dict[str, Any]) -> User:
        session = self.get_session()
        try:
            user = User(**user_data)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        finally:
            if not self._provided_session:
                session.close()

    def get_user_by_email(self, email: str) -> Optional[User]:
        session = self.get_session()
        try:
            return session.query(User).filter(User.email == email).first()
        finally:
            if not self._provided_session:
                session.close()

    def insert_lead(self, tenant_id: str, lead_data: Dict[str, Any]) -> Lead:
        session = self.get_session()
        try:
            lead = Lead(tenant_id=tenant_id, **lead_data)
            session.add(lead)
            session.commit()
            session.refresh(lead)
            return lead
        finally:
            if not self._provided_session:
                session.close()

    def _resolve_tenant_id(self, tenant_id: Optional[str]) -> str:
        resolved = tenant_id or self.tenant_id
        if not resolved:
            raise ValueError("tenant_id is required for this operation")
        return resolved

    def get_dashboard_stats(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        resolved_tenant_id = self._resolve_tenant_id(tenant_id)
        session = self.get_session()
        try:
            total = session.query(func.count(Lead.id)).filter(Lead.tenant_id == resolved_tenant_id).scalar() or 0
            avg_score = session.query(func.avg(Lead.ai_score)).filter(Lead.tenant_id == resolved_tenant_id).scalar() or 0
            booked = (
                session.query(func.count(Lead.id))
                .filter(Lead.tenant_id == resolved_tenant_id, Lead.ai_tier == "BOOK NOW")
                .scalar()
                or 0
            )
            return {
                "total_leads": total,
                "avg_score": round(float(avg_score), 1) if avg_score else 0.0,
                "book_now_count": booked,
                "conversion_rate": round((booked / total) * 100, 1) if total else 0.0,
            }
        finally:
            if not self._provided_session:
                session.close()

    def get_all_leads(self, tenant_id: Optional[str] = None, page: int = 1, page_size: int = 50) -> List[Lead]:
        resolved_tenant_id = self._resolve_tenant_id(tenant_id)
        session = self.get_session()
        try:
            return (
                session.query(Lead)
                .filter(Lead.tenant_id == resolved_tenant_id)
                .order_by(Lead.created_at.desc())
                .offset((max(page, 1) - 1) * page_size)
                .limit(page_size)
                .all()
            )
        finally:
            if not self._provided_session:
                session.close()

    def update_lead_action(self, tenant_id: str, lead_id: int, action: str) -> None:
        session = self.get_session()
        try:
            lead = (
                session.query(Lead)
                .filter(Lead.tenant_id == tenant_id, Lead.id == lead_id)
                .first()
            )
            if lead:
                lead.action_taken = action
                lead.status = "processing"
                session.commit()
        finally:
            if not self._provided_session:
                session.close()

    def update_lead_sla(
        self,
        tenant_id: str,
        lead_id: int,
        *,
        first_response_at: Optional[datetime] = None,
        first_human_contact_at: Optional[datetime] = None,
        appointment_booked_at: Optional[datetime] = None,
        retained_at: Optional[datetime] = None,
    ) -> None:
        session = self.get_session()
        try:
            lead = (
                session.query(Lead)
                .filter(Lead.tenant_id == tenant_id, Lead.id == lead_id)
                .first()
            )
            if not lead:
                return
            if first_response_at and not lead.first_response_at:
                lead.first_response_at = first_response_at
            if first_human_contact_at and not lead.first_human_contact_at:
                lead.first_human_contact_at = first_human_contact_at
            if appointment_booked_at and not lead.appointment_booked_at:
                lead.appointment_booked_at = appointment_booked_at
            if retained_at and not lead.retained_at:
                lead.retained_at = retained_at
            session.commit()
        finally:
            if not self._provided_session:
                session.close()

    def create_lead_event(
        self,
        tenant_id: str,
        lead_id: int,
        event_type: str,
        event_payload: Optional[Dict[str, Any]] = None,
    ) -> LeadEvent:
        session = self.get_session()
        try:
            event = LeadEvent(
                tenant_id=tenant_id,
                lead_id=lead_id,
                event_type=event_type,
                event_payload=event_payload or {},
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return event
        finally:
            if not self._provided_session:
                session.close()

    def create_communication_attempt(
        self,
        tenant_id: str,
        lead_id: int,
        channel: str,
        provider: str,
        payload_snapshot: Dict[str, Any],
        idempotency_key: str,
        status: str = "pending",
    ) -> CommunicationAttempt:
        session = self.get_session()
        try:
            row = (
                session.query(CommunicationAttempt)
                .filter(CommunicationAttempt.idempotency_key == idempotency_key)
                .first()
            )
            if row:
                return row
            row = CommunicationAttempt(
                tenant_id=tenant_id,
                lead_id=lead_id,
                channel=channel,
                provider=provider,
                payload_snapshot=payload_snapshot,
                status=status,
                idempotency_key=idempotency_key,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row
        finally:
            if not self._provided_session:
                session.close()

    def update_communication_attempt(
        self,
        attempt_id: int,
        *,
        status: str,
        provider_response_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
        retry_count: Optional[int] = None,
        next_retry_at: Optional[datetime] = None,
    ) -> None:
        session = self.get_session()
        try:
            row = session.query(CommunicationAttempt).filter(CommunicationAttempt.id == attempt_id).first()
            if not row:
                return
            row.status = status
            row.provider_response_id = provider_response_id
            row.failure_reason = failure_reason
            if retry_count is not None:
                row.retry_count = retry_count
            row.next_retry_at = next_retry_at
            session.commit()
            if status == "sent":
                self.update_lead_sla(
                    row.tenant_id,
                    row.lead_id,
                    first_response_at=datetime.now(timezone.utc),
                )
        finally:
            if not self._provided_session:
                session.close()

    def get_pending_communication_attempts(self, now: Optional[datetime] = None, limit: int = 100) -> List[CommunicationAttempt]:
        now = now or datetime.now(timezone.utc)
        session = self.get_session()
        try:
            return (
                session.query(CommunicationAttempt)
                .filter(
                    CommunicationAttempt.status.in_(["pending", "retry"]),
                    (
                        (CommunicationAttempt.next_retry_at.is_(None))
                        | (CommunicationAttempt.next_retry_at <= now)
                    ),
                )
                .order_by(CommunicationAttempt.created_at.asc())
                .limit(limit)
                .all()
            )
        finally:
            if not self._provided_session:
                session.close()

    def schedule_retry(
        self,
        attempt_id: int,
        failure_reason: str,
        retry_count: int,
        base_delay_seconds: int = 30,
    ) -> None:
        delay = base_delay_seconds * (2 ** max(retry_count - 1, 0))
        next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay)
        self.update_communication_attempt(
            attempt_id,
            status="retry" if retry_count < 5 else "dead_letter",
            failure_reason=failure_reason,
            retry_count=retry_count,
            next_retry_at=next_retry if retry_count < 5 else None,
        )

    def create_mercury_escalation(
        self,
        tenant_id: str,
        lead_id: int,
        level: int,
        owner_phone: str,
        escalation_key: str,
    ) -> MercuryEscalation:
        session = self.get_session()
        try:
            existing = (
                session.query(MercuryEscalation)
                .filter(MercuryEscalation.escalation_key == escalation_key)
                .first()
            )
            if existing:
                return existing
            row = MercuryEscalation(
                tenant_id=tenant_id,
                lead_id=lead_id,
                level=level,
                owner_phone=owner_phone,
                escalation_key=escalation_key,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row
        finally:
            if not self._provided_session:
                session.close()

    def get_pending_mercury_escalations(self, limit: int = 100) -> List[MercuryEscalation]:
        session = self.get_session()
        try:
            return (
                session.query(MercuryEscalation)
                .filter(MercuryEscalation.status == "pending")
                .order_by(MercuryEscalation.triggered_at.asc())
                .limit(limit)
                .all()
            )
        finally:
            if not self._provided_session:
                session.close()

    def complete_mercury_escalation(self, escalation_id: int) -> None:
        session = self.get_session()
        try:
            row = session.query(MercuryEscalation).filter(MercuryEscalation.id == escalation_id).first()
            if not row:
                return
            row.status = "accepted"
            row.accepted_at = datetime.now(timezone.utc)
            session.commit()
            self.update_lead_sla(
                row.tenant_id,
                row.lead_id,
                first_human_contact_at=datetime.now(timezone.utc),
            )
        finally:
            if not self._provided_session:
                session.close()

    def expire_mercury_escalation(self, escalation_id: int) -> None:
        session = self.get_session()
        try:
            row = session.query(MercuryEscalation).filter(MercuryEscalation.id == escalation_id).first()
            if not row or row.status != "pending":
                return
            row.status = "expired"
            session.commit()
        finally:
            if not self._provided_session:
                session.close()

    def get_open_mercury_escalation_for_lead(self, tenant_id: str, lead_id: int) -> Optional[MercuryEscalation]:
        session = self.get_session()
        try:
            return (
                session.query(MercuryEscalation)
                .filter(
                    MercuryEscalation.tenant_id == tenant_id,
                    MercuryEscalation.lead_id == lead_id,
                    MercuryEscalation.status == "pending",
                )
                .order_by(MercuryEscalation.level.asc())
                .first()
            )
        finally:
            if not self._provided_session:
                session.close()

    def get_pending_mercury_escalation_for_lead(self, tenant_id: str, lead_id: int) -> Optional[MercuryEscalation]:
        session = self.get_session()
        try:
            return (
                session.query(MercuryEscalation)
                .filter(
                    MercuryEscalation.tenant_id == tenant_id,
                    MercuryEscalation.lead_id == lead_id,
                    MercuryEscalation.status == "pending",
                )
                .order_by(MercuryEscalation.level.asc())
                .first()
            )
        finally:
            if not self._provided_session:
                session.close()

    def get_mercury_policy(self, tenant_id: str) -> MercuryEscalationPolicy:
        session = self.get_session()
        try:
            policy = (
                session.query(MercuryEscalationPolicy)
                .filter(MercuryEscalationPolicy.tenant_id == tenant_id)
                .first()
            )
            if policy:
                return policy
            policy = MercuryEscalationPolicy(
                tenant_id=tenant_id,
                contacts=[],
                timeout_seconds=120,
                max_levels=3,
                parallel=False,
            )
            session.add(policy)
            session.commit()
            session.refresh(policy)
            return policy
        finally:
            if not self._provided_session:
                session.close()

    def upsert_mercury_policy(
        self,
        tenant_id: str,
        *,
        contacts: List[str],
        timeout_seconds: int,
        max_levels: int,
        parallel: bool,
    ) -> MercuryEscalationPolicy:
        session = self.get_session()
        try:
            policy = (
                session.query(MercuryEscalationPolicy)
                .filter(MercuryEscalationPolicy.tenant_id == tenant_id)
                .first()
            )
            if not policy:
                policy = MercuryEscalationPolicy(tenant_id=tenant_id)
                session.add(policy)
            policy.contacts = contacts
            policy.timeout_seconds = timeout_seconds
            policy.max_levels = max_levels
            policy.parallel = parallel
            session.commit()
            session.refresh(policy)
            return policy
        finally:
            if not self._provided_session:
                session.close()

    @staticmethod
    def _median(values: List[float]) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        n = len(ordered)
        mid = n // 2
        if n % 2:
            return ordered[mid]
        return (ordered[mid - 1] + ordered[mid]) / 2

    def get_business_kpis(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        resolved_tenant_id = self._resolve_tenant_id(tenant_id)
        session = self.get_session()
        try:
            leads = (
                session.query(Lead)
                .filter(Lead.tenant_id == resolved_tenant_id)
                .order_by(Lead.created_at.desc())
                .limit(500)
                .all()
            )
            response_seconds: List[float] = []
            human_contact_seconds: List[float] = []
            total = len(leads)
            contacted = 0
            qualified = 0
            booked = 0
            retained = 0
            projected_fee = 0.0
            for lead in leads:
                if lead.first_response_at:
                    response_seconds.append(
                        (lead.first_response_at - lead.lead_received_at).total_seconds()
                    )
                if lead.first_human_contact_at:
                    contacted += 1
                    human_contact_seconds.append(
                        (lead.first_human_contact_at - lead.lead_received_at).total_seconds()
                    )
                if (lead.ai_score or 0) >= 7:
                    qualified += 1
                if lead.appointment_booked_at:
                    booked += 1
                if lead.retained_at:
                    retained += 1
                projected_fee += float(lead.estimated_case_value or 0) * 0.33

            return {
                "lead_count": total,
                "median_speed_to_first_response_seconds": round(self._median(response_seconds), 1),
                "median_speed_to_first_human_contact_seconds": round(self._median(human_contact_seconds), 1),
                "contact_rate_pct": round((contacted / total) * 100, 1) if total else 0.0,
                "qualified_rate_pct": round((qualified / total) * 100, 1) if total else 0.0,
                "consult_booking_rate_pct": round((booked / total) * 100, 1) if total else 0.0,
                "retained_case_rate_pct": round((retained / total) * 100, 1) if total else 0.0,
                "projected_fee_pipeline_usd": round(projected_fee, 2),
            }
        finally:
            if not self._provided_session:
                session.close()

    def get_lead_by_id(self, tenant_id: str, lead_id: int) -> Optional[Lead]:
        session = self.get_session()
        try:
            return (
                session.query(Lead)
                .filter(Lead.tenant_id == tenant_id, Lead.id == lead_id)
                .first()
            )
        finally:
            if not self._provided_session:
                session.close()

    def set_lead_status(self, tenant_id: str, lead_id: int, status: str) -> None:
        session = self.get_session()
        try:
            lead = (
                session.query(Lead)
                .filter(Lead.tenant_id == tenant_id, Lead.id == lead_id)
                .first()
            )
            if not lead:
                return
            lead.status = status
            session.commit()
        finally:
            if not self._provided_session:
                session.close()

    def get_lead_timeline(self, tenant_id: str, lead_id: int) -> List[LeadEvent]:
        session = self.get_session()
        try:
            return (
                session.query(LeadEvent)
                .filter(LeadEvent.tenant_id == tenant_id, LeadEvent.lead_id == lead_id)
                .order_by(LeadEvent.created_at.asc())
                .all()
            )
        finally:
            if not self._provided_session:
                session.close()

    def log_error(
        self,
        context: str,
        error: Exception,
        payload: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ) -> None:
        session = self.get_session()
        try:
            row = ErrorLog(
                tenant_id=tenant_id,
                context=context,
                error_type=error.__class__.__name__,
                message=str(error),
                payload=payload or {},
            )
            session.add(row)
            session.commit()
        finally:
            if not self._provided_session:
                session.close()
