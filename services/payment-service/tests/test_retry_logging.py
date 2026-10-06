"""Tests for structured logging in /payments/process-with-retry (FACTORY-PAY)."""

import logging
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import main  # noqa: E402

LOGGER_NAME = "payment_service.retry"
SENSITIVE_MARKER = "4111111111111111"

PAYLOAD = {
    "user_id": "user-123",
    "amount": 42.5,
    "currency": "USD",
    "description": f"card {SENSITIVE_MARKER} cvv 999",
}


class _FakeAsyncClient:
    """Stands in for httpx.AsyncClient so the failure notification never hits the network."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, *args, **kwargs):
        return None


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    sleeps = []

    async def _no_sleep(delay, *args, **kwargs):
        sleeps.append(delay)

    monkeypatch.setattr(main.asyncio, "sleep", _no_sleep)
    monkeypatch.setattr(main.httpx, "AsyncClient", _FakeAsyncClient)
    main.payments_db.clear()
    yield sleeps
    main.payments_db.clear()


@pytest.fixture
def client():
    return TestClient(main.app)


def _flaky(fail_times):
    """Wrap the real attempt so it fails the first `fail_times` calls."""
    real = main._attempt_payment
    calls = {"n": 0}

    def _attempt(payment_id, request, attempt):
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise RuntimeError("gateway timeout")
        return real(payment_id, request, attempt)

    return _attempt


def _records(caplog, event):
    return [r for r in caplog.records if r.name == LOGGER_NAME and getattr(r, "event", None) == event]


def _assert_no_sensitive_data(caplog):
    for r in caplog.records:
        blob = r.getMessage() + " " + repr(r.__dict__)
        assert SENSITIVE_MARKER not in blob
        assert "cvv" not in blob.lower()


def test_success_after_retry_logs_once(client, caplog, monkeypatch, _isolate):
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    monkeypatch.setattr(main, "_attempt_payment", _flaky(fail_times=1))

    resp = client.post("/payments/process-with-retry", json=PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["attempts"] == 2
    assert _isolate == [1]  # backoff timing unchanged

    succeeded = _records(caplog, "payment.retry.succeeded")
    assert len(succeeded) == 1
    rec = succeeded[0]
    assert rec.levelno == logging.INFO
    assert rec.attempt == 2 and rec.attempt > 1
    assert rec.max_attempts == 3
    assert rec.outcome == "success"
    assert rec.payment_id == body["id"]
    assert isinstance(rec.duration_ms, float)

    failed = _records(caplog, "payment.retry.attempt_failed")
    assert len(failed) == 1
    assert failed[0].error_type == "RuntimeError"
    assert _records(caplog, "payment.retry.exhausted") == []
    _assert_no_sensitive_data(caplog)


def test_first_attempt_success_emits_no_retry_succeeded(client, caplog):
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)

    resp = client.post("/payments/process-with-retry", json=PAYLOAD)

    assert resp.status_code == 200
    assert resp.json()["attempts"] == 1
    assert _records(caplog, "payment.retry.succeeded") == []
    assert len(_records(caplog, "payment.process.succeeded")) == 1
    _assert_no_sensitive_data(caplog)


def test_retries_exhausted_logs_once(client, caplog, monkeypatch, _isolate):
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    monkeypatch.setattr(main, "_attempt_payment", _flaky(fail_times=99))

    resp = client.post("/payments/process-with-retry", json=PAYLOAD)

    # Contract unchanged
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Payment failed after 3 attempts"}
    assert _isolate == [1, 5]

    exhausted = _records(caplog, "payment.retry.exhausted")
    assert len(exhausted) == 1
    rec = exhausted[0]
    assert rec.levelno >= logging.WARNING
    assert rec.attempt == rec.max_attempts == 3
    assert rec.error_type == "RuntimeError"
    assert rec.error_message == "gateway timeout"
    assert rec.outcome == "failure"

    assert _records(caplog, "payment.retry.succeeded") == []
    assert len(_records(caplog, "payment.retry.attempt_failed")) == 2
    _assert_no_sensitive_data(caplog)


def test_logging_failure_does_not_change_result(client, monkeypatch):
    def _broken_log(*args, **kwargs):
        raise RuntimeError("logging backend down")

    monkeypatch.setattr(main.logger, "log", _broken_log)
    monkeypatch.setattr(main, "_attempt_payment", _flaky(fail_times=1))
    resp = client.post("/payments/process-with-retry", json=PAYLOAD)
    assert resp.status_code == 200
    assert resp.json()["attempts"] == 2

    monkeypatch.setattr(main, "_attempt_payment", _flaky(fail_times=99))
    resp = client.post("/payments/process-with-retry", json=PAYLOAD)
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Payment failed after 3 attempts"}
