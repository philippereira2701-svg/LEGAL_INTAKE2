"""
Nightly retention enforcement worker.
Hard-deletes records past retention windows and writes deletion receipts to audit log.
"""

from __future__ import annotations

from celery.schedules import crontab

from src.retention.deletion_service import DeletionService


def register_retention_schedule(celery_app, deletion_service: DeletionService) -> None:
    celery_app.conf.beat_schedule = {
        "lexbridge-nightly-retention-0200-utc": {
            "task": "retention.enforce",
            "schedule": crontab(hour=2, minute=0),
        }
    }

    @celery_app.task(name="retention.enforce")
    def retention_enforce():
        return deletion_service.run_nightly_retention_enforcement()
