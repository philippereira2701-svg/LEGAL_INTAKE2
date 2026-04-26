"""
PII scrubber used before logging or transmitting errors to external telemetry systems.
"""

from __future__ import annotations

import re
from typing import Any


class PIIScrubber:
    def __init__(self, phi_fields: list[str]):
        self.phi_fields = set(phi_fields)

    def scrub_dict(self, payload: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in payload.items():
            if key in self.phi_fields:
                result[key] = "[REDACTED]"
            elif isinstance(value, dict):
                result[key] = self.scrub_dict(value)
            elif isinstance(value, list):
                result[key] = [self.scrub_dict(v) if isinstance(v, dict) else self.scrub_text(str(v)) for v in value]
            else:
                result[key] = self.scrub_text(str(value))
        return result

    def scrub_text(self, text: str) -> str:
        text = re.sub(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "[REDACTED_EMAIL]", text)
        text = re.sub(r"(?:\+?1[\s\-\.]?)?(?:\(?\d{3}\)?[\s\-\.]?)\d{3}[\s\-\.]?\d{4}", "[REDACTED_PHONE]", text)
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", text)
        text = re.sub(r"\b(19|20)\d{2}-\d{2}-\d{2}\b", "[REDACTED_DATE]", text)
        return text
