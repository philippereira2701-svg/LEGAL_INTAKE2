"""
Key provider abstraction for encryption.
Supports AWS KMS in production and env-key provider in development only.
"""

from __future__ import annotations

import abc
import base64
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class KeyMaterial:
    key_version: str
    key_bytes: bytes


class KMSKeyProvider(abc.ABC):
    @abc.abstractmethod
    def get_key(self, key_version: Optional[str] = None) -> KeyMaterial:
        raise NotImplementedError

    @abc.abstractmethod
    def get_active_key(self) -> KeyMaterial:
        raise NotImplementedError


class AWSKMSProvider(KMSKeyProvider):
    def __init__(self, kms_client, alias_name: str, active_key_version: str):
        self.kms_client = kms_client
        self.alias_name = alias_name
        self.active_key_version = active_key_version

    def _fetch_plaintext_key(self, key_version: str) -> bytes:
        response = self.kms_client.generate_data_key_without_plaintext(
            KeyId=f"{self.alias_name}:{key_version}",
            KeySpec="AES_256",
        )
        ciphertext_blob = response["CiphertextBlob"]
        decrypted = self.kms_client.decrypt(CiphertextBlob=ciphertext_blob)
        return decrypted["Plaintext"]

    def get_key(self, key_version: Optional[str] = None) -> KeyMaterial:
        resolved = key_version or self.active_key_version
        return KeyMaterial(key_version=resolved, key_bytes=self._fetch_plaintext_key(resolved))

    def get_active_key(self) -> KeyMaterial:
        return self.get_key(self.active_key_version)


class EnvKeyProvider(KMSKeyProvider):
    def __init__(self, active_key_version: str = "v1"):
        app_env = os.getenv("APP_ENV", "development").lower()
        if app_env != "development":
            raise RuntimeError("EnvKeyProvider is development-only and cannot run in production.")
        self.active_key_version = active_key_version

    def _read_key_from_env(self, key_version: str) -> bytes:
        env_name = f"LEXBRIDGE_FIELD_KEY_{key_version.upper()}"
        raw_key = os.getenv(env_name)
        if not raw_key:
            raise RuntimeError(f"Missing env key material: {env_name}")
        return base64.urlsafe_b64decode(raw_key.encode("utf-8"))

    def get_key(self, key_version: Optional[str] = None) -> KeyMaterial:
        resolved = key_version or self.active_key_version
        return KeyMaterial(key_version=resolved, key_bytes=self._read_key_from_env(resolved))

    def get_active_key(self) -> KeyMaterial:
        return self.get_key(self.active_key_version)
