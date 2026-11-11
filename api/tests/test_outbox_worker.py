import pytest

from app.config import settings
from app.worker import publish_outbox_once, retry_delay_seconds


def test_outbox_retry_delay_is_exponential_and_bounded():
    assert retry_delay_seconds(1) == 30
    assert retry_delay_seconds(2) == 60
    assert retry_delay_seconds(3) == 120
    assert retry_delay_seconds(50) == 3600


def test_outbox_is_idle_when_no_webhook_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "outbox_webhook_url", None)
    assert publish_outbox_once() == 0
