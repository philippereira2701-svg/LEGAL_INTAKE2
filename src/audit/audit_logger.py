"""
Centralized HIPAA audit logger.
Captures PHI access events without storing PHI values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AuditEvent:
    user_id: str
    tenant_id: str
    action: str
    resource_type: str
    resource_id: str
    ip_address: str
    user_agent: str
    timestamp: str


class AuditLogger:
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory

    def log(
        self,
        *,
        user_id: str,
        tenant_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        ip_address: str,
        user_agent: str,
    ) -> AuditEvent:
        event = AuditEvent(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        session = self.db_session_factory()
        try:
            session.execute(
                """
                INSERT INTO audit_log
                (user_id, tenant_id, action, resource_type, resource_id, ip_address, user_agent, timestamp)
                VALUES (:user_id, :tenant_id, :action, :resource_type, :resource_id, :ip_address, :user_agent, :timestamp)
                """,
                event.__dict__,
            )
            session.commit()
        finally:
            session.close()
        return event
