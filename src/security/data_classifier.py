"""
Data classifier for training firewall guarantees.
Prevents PHI data from being sent to training destinations.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class DataClass(str, Enum):
    PHI = "PHI"
    NON_PHI = "NON_PHI"


class DataDestination(str, Enum):
    TRAINING_PIPELINE = "TRAINING_PIPELINE"
    APPLICATION_RUNTIME = "APPLICATION_RUNTIME"


class PHITrainingViolationError(Exception):
    pass


class DataAccessClassifier:
    def __init__(self, phi_fields: list[str], audit_logger):
        self.phi_fields = set(phi_fields)
        self.audit_logger = audit_logger

    def classify(self, row: dict[str, Any]) -> DataClass:
        return DataClass.PHI if any(key in self.phi_fields for key in row.keys()) else DataClass.NON_PHI

    def enforce_destination_policy(self, row: dict[str, Any], destination: DataDestination, user_id: str, tenant_id: str) -> None:
        data_class = self.classify(row)
        if destination == DataDestination.TRAINING_PIPELINE and data_class == DataClass.PHI:
            self.audit_logger.log(
                user_id=user_id,
                tenant_id=tenant_id,
                action="PHI_TRAINING_VIOLATION",
                resource_type="training_export",
                resource_id="blocked",
                ip_address="127.0.0.1",
                user_agent="data_classifier",
            )
            raise PHITrainingViolationError("Attempted to send PHI to training pipeline.")
