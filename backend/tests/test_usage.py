from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.config import get_settings
from app.main import app
from app.usage import UsageLimitError, UsageTrackerError, limit_message, resolve_client_ip, usage_windows


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_usage_windows_follow_utc():
    moment = datetime(2026, 11, 20, 15, 8, 30, tzinfo=timezone(timedelta(hours=-5)))
    day, hour = usage_windows(moment)
    assert day == datetime(2026, 11, 20, 0, 0, tzinfo=timezone.utc)
    assert hour == datetime(2026, 11, 20, 20, 0, tzinfo=timezone.utc)


def test_client_ip_uses_the_last_forwarded_hop_when_a_proxy_is_trusted():
    assert resolve_client_ip("1.1.1.1, 203.0.113.5", "10.0.0.4", trust_proxy=True) == "203.0.113.5"
    assert resolve_client_ip(None, "127.0.0.1", trust_proxy=True) == "127.0.0.1"
    assert resolve_client_ip("1.1.1.1", "127.0.0.1", trust_proxy=False) == "127.0.0.1"


def test_limit_messages_name_the_cap():
    assert "100" in limit_message("day", "investigate", 100)
    assert "00:00 UTC" in limit_message("day", "ask", 300)
    assert "this network" in limit_message("hour", "investigate", 10)


def test_investigate_returns_429_without_calling_azure(monkeypatch, client):
    monkeypatch.setattr(routes, "require_retrieval_ready", lambda: None)
    monkeypatch.setattr(routes, "run_investigation", lambda: (_ for _ in ()).throw(AssertionError("Azure was called")))
    monkeypatch.setenv("USAGE_LIMITS_ENABLED", "true")
    get_settings.cache_clear()

    def deny(route, ip, now=None):
        raise UsageLimitError("day", route, 100)

    monkeypatch.setattr("app.usage.consume_usage", deny)
    try:
        response = client.post("/api/investigate")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 429
    detail = response.json()["detail"]
    assert detail["error"] == "usage_limit"
    assert detail["scope"] == "day"
    assert "100" in detail["message"]


def test_ask_returns_503_when_the_counter_cannot_be_written(monkeypatch, client):
    monkeypatch.setattr(routes, "require_retrieval_ready", lambda: None)
    monkeypatch.setattr(routes, "run_ask", lambda request: (_ for _ in ()).throw(AssertionError("Azure was called")))
    monkeypatch.setenv("USAGE_LIMITS_ENABLED", "true")
    get_settings.cache_clear()

    def broken(route, ip, now=None):
        raise UsageTrackerError("down")

    monkeypatch.setattr("app.usage.consume_usage", broken)
    try:
        response = client.post("/api/ask", json={"question": "Who decides the loan?"})
    finally:
        get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "usage_tracker_unavailable"


def test_a_missing_azure_configuration_does_not_spend_the_cap(monkeypatch, client):
    called = {"n": 0}

    def consume(route, ip, now=None):
        called["n"] += 1

    monkeypatch.setattr(routes, "missing_azure", lambda: ["AZURE_OPENAI_API_KEY"])
    monkeypatch.setattr("app.usage.consume_usage", consume)
    response = client.post("/api/investigate")
    assert response.status_code == 503
    assert called["n"] == 0
