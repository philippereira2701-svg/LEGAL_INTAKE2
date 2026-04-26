"""
Safe serializer that blocks PHI exposure in API responses unless explicitly authorized.
"""

from __future__ import annotations

from typing import Any


class UnsafePIIResponseError(Exception):
    pass


class SafeSerializer:
    def __init__(self, phi_fields: list[str]):
        self.phi_fields = set(phi_fields)

    def serialize(self, payload: dict[str, Any], include_pii: bool = False) -> dict[str, Any]:
        if include_pii:
            return payload
        leaked = [key for key in payload.keys() if key in self.phi_fields]
        if leaked:
            raise UnsafePIIResponseError(f"Response includes PHI fields without include_pii=True: {leaked}")
        return payload
