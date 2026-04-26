"""
Field-level encryption service for PHI.
Encrypts before persistence and decrypts after retrieval with per-row key version metadata.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from cryptography.fernet import Fernet

from src.security.kms_provider import KMSKeyProvider


@dataclass
class EncryptedField:
    ciphertext: str
    key_version: str
    field_id: str
    encrypted_at: str
    value_hash: str


@dataclass
class RotationReport:
    table: str
    old_version: str
    new_version: str
    total_rows_scanned: int
    total_rows_rotated: int
    started_at: str
    completed_at: str


class EncryptionService:
    def __init__(self, key_provider: KMSKeyProvider, hmac_secret: bytes):
        self.key_provider = key_provider
        self.hmac_secret = hmac_secret

    def _fernet_for_version(self, key_version: str) -> Fernet:
        km = self.key_provider.get_key(key_version)
        return Fernet(base64.urlsafe_b64encode(km.key_bytes[:32]))

    def _active_fernet(self) -> tuple[Fernet, str]:
        km = self.key_provider.get_active_key()
        return Fernet(base64.urlsafe_b64encode(km.key_bytes[:32])), km.key_version

    def _hmac_hash(self, value: str, field_id: str) -> str:
        digest = hmac.new(
            self.hmac_secret,
            msg=f"{field_id}:{value}".encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return digest

    def encrypt_field(self, value: str, field_id: str) -> EncryptedField:
        fernet, key_version = self._active_fernet()
        encrypted = fernet.encrypt(value.encode("utf-8")).decode("utf-8")
        return EncryptedField(
            ciphertext=encrypted,
            key_version=key_version,
            field_id=field_id,
            encrypted_at=datetime.now(timezone.utc).isoformat(),
            value_hash=self._hmac_hash(value, field_id),
        )

    def decrypt_field(self, encrypted: EncryptedField) -> str:
        fernet = self._fernet_for_version(encrypted.key_version)
        return fernet.decrypt(encrypted.ciphertext.encode("utf-8")).decode("utf-8")

    def encrypt_record(self, data: Dict[str, Any], phi_fields: List[str]) -> Dict[str, Any]:
        encrypted_data: Dict[str, Any] = dict(data)
        for field in phi_fields:
            raw = data.get(field)
            if raw in (None, ""):
                continue
            enc = self.encrypt_field(str(raw), field)
            encrypted_data[f"{field}_encrypted"] = json.dumps(enc.__dict__)
            encrypted_data[f"{field}_hash"] = enc.value_hash
            encrypted_data.pop(field, None)
        return encrypted_data

    def decrypt_record(self, data: Dict[str, Any], phi_fields: List[str]) -> Dict[str, Any]:
        decrypted_data: Dict[str, Any] = dict(data)
        for field in phi_fields:
            payload = data.get(f"{field}_encrypted")
            if not payload:
                continue
            parsed = EncryptedField(**json.loads(payload))
            decrypted_data[field] = self.decrypt_field(parsed)
        return decrypted_data

    def rotate_key(self, old_version: str, new_version: str, table: str) -> RotationReport:
        started = datetime.now(timezone.utc).isoformat()
        # Rotation must execute in an async/background job that scans rows and re-encrypts.
        # This method returns a report contract; caller performs DB iteration and updates.
        completed = datetime.now(timezone.utc).isoformat()
        return RotationReport(
            table=table,
            old_version=old_version,
            new_version=new_version,
            total_rows_scanned=0,
            total_rows_rotated=0,
            started_at=started,
            completed_at=completed,
        )
