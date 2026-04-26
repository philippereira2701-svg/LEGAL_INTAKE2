from services.communications import CommunicationsService


class FakeAttempt:
    def __init__(self, attempt_id=10):
        self.id = attempt_id
        self.tenant_id = "tenant-1"
        self.lead_id = 99
        self.retry_count = 0
        self.payload_snapshot = {"client_phone": "+15550001111", "message": "hello"}
        self.channel = "sms"


class FakeDB:
    def __init__(self):
        self.updated = []
        self.events = []
        self.scheduled = []

    def update_communication_attempt(self, attempt_id, **kwargs):
        self.updated.append((attempt_id, kwargs))

    def create_lead_event(self, tenant_id, lead_id, event_type, event_payload):
        self.events.append((tenant_id, lead_id, event_type, event_payload))

    def schedule_retry(self, attempt_id, failure_reason, retry_count, base_delay_seconds=30):
        self.scheduled.append((attempt_id, failure_reason, retry_count))


def test_deliver_attempt_persists_success(monkeypatch):
    db = FakeDB()
    service = CommunicationsService(db)  # type: ignore[arg-type]
    attempt = FakeAttempt()

    def fake_send(_payload, _tenant):
        return "SM123"

    monkeypatch.setattr(service, "_send_sms", fake_send)
    service.deliver_attempt(attempt, {"twilio_sid": "x", "twilio_token": "y", "twilio_phone": "+1"})

    assert db.updated[0][1]["status"] == "sent"
    assert db.events[0][2] == "communication.sent"


def test_deliver_attempt_schedules_retry_on_failure(monkeypatch):
    db = FakeDB()
    service = CommunicationsService(db)  # type: ignore[arg-type]
    attempt = FakeAttempt()

    def fake_send(_payload, _tenant):
        raise RuntimeError("provider down")

    monkeypatch.setattr(service, "_send_sms", fake_send)
    service.deliver_attempt(attempt, {"twilio_sid": "x", "twilio_token": "y", "twilio_phone": "+1"})

    assert db.scheduled[0][0] == attempt.id
    assert "provider down" in db.scheduled[0][1]
    assert db.events[0][2] == "communication.failed"
