"""
Business Associate Agreement service.
Provides BAA generation, signature recording, and status verification.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone


class BAAService:
    def __init__(self, db_session_factory, encryption_service):
        self.db_session_factory = db_session_factory
        self.encryption_service = encryption_service

    def generate_baa_document(self, tenant_id: str) -> str:
        session = self.db_session_factory()
        try:
            tenant = session.execute("SELECT firm_name FROM tenants WHERE id = :tenant_id", {"tenant_id": tenant_id}).fetchone()
            firm_name = tenant[0] if tenant else "Unknown Firm"
            return (
                "BUSINESS ASSOCIATE AGREEMENT\n"
                f"Firm: {firm_name}\n"
                f"Effective Date: {datetime.now(timezone.utc).date().isoformat()}\n"
                "This template requires legal review by qualified HIPAA counsel.\n"
            )
        finally:
            session.close()

    def record_baa_signature(self, tenant_id: str, signatory_name: str, signatory_email: str, ip_address: str, timestamp: str) -> None:
        name_enc = self.encryption_service.encrypt_field(signatory_name, "signatory_name")
        email_enc = self.encryption_service.encrypt_field(signatory_email, "signatory_email")
        doc_content = self.generate_baa_document(tenant_id)
        doc_hash = hashlib.sha256(doc_content.encode("utf-8")).hexdigest()

        session = self.db_session_factory()
        try:
            session.execute(
                """
                INSERT INTO baa_signatures
                (tenant_id, signatory_name_encrypted, signatory_email_encrypted, signed_at, signing_ip, document_hash, version)
                VALUES (:tenant_id, :name_enc, :email_enc, :signed_at, :signing_ip, :document_hash, :version)
                """,
                {
                    "tenant_id": tenant_id,
                    "name_enc": name_enc.ciphertext,
                    "email_enc": email_enc.ciphertext,
                    "signed_at": timestamp,
                    "signing_ip": ip_address,
                    "document_hash": doc_hash,
                    "version": "v1",
                },
            )
            session.execute("UPDATE tenants SET baa_signed = TRUE WHERE id = :tenant_id", {"tenant_id": tenant_id})
            session.commit()
        finally:
            session.close()

    def verify_baa_status(self, tenant_id: str) -> bool:
        session = self.db_session_factory()
        try:
            row = session.execute("SELECT baa_signed FROM tenants WHERE id = :tenant_id", {"tenant_id": tenant_id}).fetchone()
            return bool(row[0]) if row else False
        finally:
            session.close()
