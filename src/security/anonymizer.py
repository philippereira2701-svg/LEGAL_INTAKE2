"""
HIPAA Safe Harbor oriented anonymization service for future opt-in training.
Must remain gated behind TRAIN_ON_CLIENT_DATA policy flag.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


SAFE_HARBOR_FIELDS = {
    "full_name",
    "phone",
    "email",
    "dob",
    "address",
    "ssn",
    "policy_number",
}


class Anonymizer:
    def anonymize_record(self, payload: dict[str, Any]) -> dict[str, Any]:
        out = dict(payload)
        for key in list(out.keys()):
            if key in SAFE_HARBOR_FIELDS:
                out[key] = f"TOKEN_{key.upper()}"

        if "incident_description" in out and isinstance(out["incident_description"], str):
            out["incident_description"] = self._redact_names_and_contacts(out["incident_description"])

        for key, value in out.items():
            if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                out[key] = value[:4]
        return out

    @staticmethod
    def _redact_names_and_contacts(text: str) -> str:
        text = re.sub(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "[EMAIL]", text)
        text = re.sub(r"(?:\+?1[\s\-\.]?)?(?:\(?\d{3}\)?[\s\-\.]?)\d{3}[\s\-\.]?\d{4}", "[PHONE]", text)
        text = re.sub(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", "[NAME]", text)
        return text
