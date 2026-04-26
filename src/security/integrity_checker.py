"""
Integrity checker for encrypted payloads.
Validates SHA-256 digest before serving data.
"""

from __future__ import annotations

import hashlib


class DataIntegrityError(Exception):
    pass


class IntegrityChecker:
    @staticmethod
    def compute_payload_hash(encrypted_payload: str) -> str:
        return hashlib.sha256(encrypted_payload.encode("utf-8")).hexdigest()

    @staticmethod
    def verify(encrypted_payload: str, expected_hash: str) -> None:
        actual_hash = IntegrityChecker.compute_payload_hash(encrypted_payload)
        if actual_hash != expected_hash:
            raise DataIntegrityError("Encrypted payload integrity check failed.")
