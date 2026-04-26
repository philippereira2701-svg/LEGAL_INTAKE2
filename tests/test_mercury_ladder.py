from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from workers import process_pending_mercury_escalations_task


class FakeSession:
    def __init__(self, tenant):
        self._tenant = tenant

    def query(self, _model):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._tenant

    def close(self):
        return None


class FakeDB:
    def __init__(self):
        self.events = []
        self.expired = []
        self.created_escalations = []
        self.created_attempts = []
        self._pending = [
            SimpleNamespace(
                id=1,
                tenant_id="tenant-1",
                lead_id=101,
                level=1,
                status="pending",
                triggered_at=datetime.now(timezone.utc) - timedelta(seconds=200),
            )
        ]

    def get_pending_mercury_escalations(self, limit=100):
        return self._pending

    def get_mercury_policy(self, tenant_id):
        return SimpleNamespace(tenant_id=tenant_id, contacts=["+15550000002", "+15550000003"], timeout_seconds=60, max_levels=3)

    def create_lead_event(self, *args, **kwargs):
        self.events.append((args, kwargs))

    def expire_mercury_escalation(self, escalation_id):
        self.expired.append(escalation_id)

    def create_mercury_escalation(self, **kwargs):
        esc = SimpleNamespace(id=2, **kwargs)
        self.created_escalations.append(esc)
        return esc

    def create_communication_attempt(self, **kwargs):
        attempt = SimpleNamespace(id=11, **kwargs)
        self.created_attempts.append(attempt)
        return attempt

    def log_error(self, *_args, **_kwargs):
        return None


def test_mercury_ladder_advances_level(monkeypatch):
    fake_db = FakeDB()
    fake_tenant = SimpleNamespace(id="tenant-1", lawyer_phone="+15550000001")
    fake_session = FakeSession(fake_tenant)

    monkeypatch.setattr("workers.SessionLocal", lambda: fake_session)
    monkeypatch.setattr("workers.DatabaseManager", lambda _session: fake_db)

    result = process_pending_mercury_escalations_task.run()

    assert result["advanced"] == 1
    assert fake_db.expired == [1]
    assert len(fake_db.created_escalations) == 1
    assert fake_db.created_escalations[0].level == 2
    assert len(fake_db.created_attempts) == 1
