"""Local rehearsal of factory webhook routing and scorecard-fail writeback."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

os.environ.setdefault("FACTORY_DRY_RUN", "1")

from agents.webhook_handler import app, _payload_from_workflow


def test_payload_flat_and_envelope():
    flat = _payload_from_workflow(
        {
            "jira_key": "PAY-12",
            "title": "Logging",
            "description": "Add logs",
            "service_id": "payment-service",
        }
    )
    assert flat.jira_key == "PAY-12"

    envelope = _payload_from_workflow(
        {
            "entityIdentifier": "PAY-12",
            "outputs": {
                "trigger": {
                    "identifier": "PAY-12",
                    "title": "Logging",
                    "properties": {"description": "Add logs", "architectureSpec": "plan"},
                    "relations": {"service": "payment-service"},
                }
            },
        }
    )
    assert envelope.service_id == "payment-service"
    assert envelope.architecture_spec == "plan"


def test_unknown_classic_action_does_not_default_to_architect():
    client = TestClient(app)
    response = client.post("/webhook/action?action_id=not_a_real_action")
    assert response.status_code == 400


def test_review_code_routes_to_reviewer():
    client = TestClient(app)
    with patch("agents.webhook_handler._execute_role"):
        response = client.post(
            "/webhook/action?action_id=review_code",
            json={"jira_key": "PAY-12", "pr_url": "https://github.com/org/repo/pull/1"},
        )
    assert response.status_code == 202
    assert response.json()["role"] == "reviewer"


def test_factory_architect_accepted():
    client = TestClient(app)
    with patch("agents.webhook_handler._execute_role"):
        response = client.post(
            "/factory/architect",
            json={
                "jira_key": "PAY-12",
                "title": "Add logging",
                "description": "Add structured success/failure logging to process-with-retry",
                "service_id": "payment-service",
                "service_path": "services/payment-service",
            },
        )
    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["role"] == "architect"


def test_github_put_file_rejects_path_escape():
    from tools.github_api import GitHubClient

    client = GitHubClient()
    client.dry_run = True
    result = client.put_file(
        "agents/base.py",
        "x",
        "msg",
        "factory/pay-12",
        "services/payment-service",
    )
    assert "error" in result


def test_github_put_file_dry_run_writes_under_service(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from tools.github_api import GitHubClient

    client = GitHubClient()
    client.dry_run = True
    path = "services/payment-service/src/note.txt"
    result = client.put_file(path, "hello", "msg", "factory/pay-12", "services/payment-service")
    assert result.get("dry_run") is True
    assert (tmp_path / path).read_text() == "hello"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
