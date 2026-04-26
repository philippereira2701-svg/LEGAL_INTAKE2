"""
Hard-delete service for PHI retention enforcement.
Generates deletion certificates for compliance evidence.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict

from src.audit.audit_logger import AuditLogger


@dataclass
class DeletionRunResult:
    run_id: str
    deleted_counts: Dict[str, int]
    timestamp: str
    manifest_hash: str


class DeletionService:
    def __init__(self, db_session_factory, audit_logger: AuditLogger):
        self.db_session_factory = db_session_factory
        self.audit_logger = audit_logger

    def delete_lead(self, lead_id: str) -> None:
        session = self.db_session_factory()
        try:
            session.execute("DELETE FROM leads WHERE id = :lead_id", {"lead_id": lead_id})
            session.commit()
        finally:
            session.close()

    def delete_tenant_data(self, tenant_id: str) -> None:
        session = self.db_session_factory()
        try:
            session.execute("DELETE FROM leads WHERE tenant_id = :tenant_id", {"tenant_id": tenant_id})
            session.commit()
        finally:
            session.close()

    def run_nightly_retention_enforcement(self) -> Dict[str, str]:
        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        lead_deleted = 0
        session = self.db_session_factory()
        try:
            result_rejected = session.execute(
                """
                DELETE FROM leads
                WHERE status = 'rejected'
                AND created_at < :threshold
                RETURNING id, tenant_id
                """,
                {"threshold": now - timedelta(days=30)},
            )
            rejected_rows = result_rejected.fetchall()
            lead_deleted += len(rejected_rows)

            result_resolved = session.execute(
                """
                DELETE FROM leads
                WHERE status = 'resolved'
                AND created_at < :threshold
                RETURNING id, tenant_id
                """,
                {"threshold": now - timedelta(days=90)},
            )
            resolved_rows = result_resolved.fetchall()
            lead_deleted += len(resolved_rows)
            session.commit()
        finally:
            session.close()

        payload = {"run_id": run_id, "deleted_counts": {"leads": lead_deleted}, "timestamp": now.isoformat()}
        manifest_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

        self.audit_logger.log(
            user_id="system",
            tenant_id="system",
            action="DELETE",
            resource_type="retention_run",
            resource_id=run_id,
            ip_address="127.0.0.1",
            user_agent="retention_worker",
        )

        self.generate_deletion_certificate(run_id, payload["deleted_counts"], manifest_hash)
        return {"run_id": run_id, "manifest_hash": manifest_hash}

    def generate_deletion_certificate(self, deletion_run_id: str, deleted_counts: Dict[str, int] | None = None, manifest_hash: str | None = None) -> str:
        deleted_counts = deleted_counts or {}
        manifest_hash = manifest_hash or hashlib.sha256(
            json.dumps({"run_id": deletion_run_id, "deleted_counts": deleted_counts}, sort_keys=True).encode("utf-8")
        ).hexdigest()
        certificate_path = f"deletion_certificate_{deletion_run_id}.pdf"
        # Placeholder PDF output for now; replace with reportlab in production pipeline.
        with open(certificate_path, "wb") as handle:
            content = (
                f"LexBridge Deletion Certificate\nRun ID: {deletion_run_id}\n"
                f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
                f"Deleted Counts: {json.dumps(deleted_counts)}\n"
                f"Manifest Hash: {manifest_hash}\n"
            )
            handle.write(content.encode("utf-8"))
        return certificate_path
