from types import SimpleNamespace

from services.mercury_mode import MercuryModeService


class FakeDB:
    def __init__(self):
        self.escalations = []
        self.attempts = []
        self.events = []
        self.policy = SimpleNamespace(contacts=[], timeout_seconds=120, max_levels=3, parallel=False)

    def get_mercury_policy(self, _tenant_id):
        return self.policy

    def get_open_mercury_escalation_for_lead(self, _tenant_id, _lead_id):
        return None

    def create_mercury_escalation(self, **kwargs):
        esc = SimpleNamespace(id=1, **kwargs)
        self.escalations.append(esc)
        return esc

    def create_communication_attempt(self, **kwargs):
        attempt = SimpleNamespace(id=10, **kwargs)
        self.attempts.append(attempt)
        return attempt

    def create_lead_event(self, *args, **kwargs):
        self.events.append((args, kwargs))


def test_mercury_triggers_for_high_score():
    db = FakeDB()
    svc = MercuryModeService(db)  # type: ignore[arg-type]
    lead = SimpleNamespace(id=123, ai_score=9)
    triggered = svc.maybe_trigger("tenant-1", lead, "+15551234567")

    assert triggered is True
    assert len(db.escalations) == 1
    assert len(db.attempts) == 1


def test_mercury_skips_low_score():
    db = FakeDB()
    svc = MercuryModeService(db)  # type: ignore[arg-type]
    lead = SimpleNamespace(id=123, ai_score=6)
    triggered = svc.maybe_trigger("tenant-1", lead, "+15551234567")

    assert triggered is False
    assert len(db.escalations) == 0
