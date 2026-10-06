#!/usr/bin/env python3
"""Golden-path rehearsal without waiting on live Jira.

1. Upserts a failing ticket (empty description) and a payment-service ticket.
2. Posts the Architect factory webhook (requires ANTHROPIC_API_KEY for a live agent run).
   Use --routing-only to skip Claude.

Usage:
  python scripts/rehearse_factory.py --routing-only
  python scripts/rehearse_factory.py --live
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from tools.port_api import PortAPIClient

FAIL_KEY = "FACTORY-FAIL"
PAY_KEY = "FACTORY-PAY"
GOLDEN_DESCRIPTION = (
    "Add structured success/failure logging to payment-service process-with-retry. "
    "Log when a retry succeeds and when it ultimately fails, without changing payment semantics."
)


def upsert_demo_tickets(port: PortAPIClient) -> None:
    fail = port.upsert_entity(
        "jiraIssue",
        FAIL_KEY,
        title="[factory fail] empty description",
        properties={
            "status": "In Progress",
            "description": "",
            "factoryStage": "Triage",
            "issueType": "Task",
        },
        relations={"service": "payment-service"},
    )
    pay = port.upsert_entity(
        "jiraIssue",
        PAY_KEY,
        title="Add structured logging to process-with-retry",
        properties={
            "status": "In Progress",
            "description": GOLDEN_DESCRIPTION,
            "factoryStage": "Triage",
            "issueType": "Task",
        },
        relations={"service": "payment-service"},
    )
    print("FAIL ticket:", json.dumps(fail)[:400])
    print("PAY ticket:", json.dumps(pay)[:400])


def post_architect(base_url: str) -> None:
    url = f"{base_url.rstrip('/')}/factory/architect"
    payload = {
        "jira_key": PAY_KEY,
        "title": "Add structured logging to process-with-retry",
        "description": GOLDEN_DESCRIPTION,
        "service_id": "payment-service",
        "service_path": "services/payment-service",
    }
    response = requests.post(url, json=payload, timeout=10)
    print("Architect dispatch:", response.status_code, response.text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="POST to local runner")
    parser.add_argument("--routing-only", action="store_true")
    parser.add_argument("--runner", default=os.getenv("FACTORY_PUBLIC_URL", "http://127.0.0.1:8000"))
    args = parser.parse_args()

    port = PortAPIClient()
    upsert_demo_tickets(port)

    fail_entity = port.get_entity(FAIL_KEY, "jiraIssue")
    pay_entity = port.get_entity(PAY_KEY, "jiraIssue")
    print("FAIL description empty:", not (fail_entity.get("properties") or {}).get("description"))
    print("PAY has description:", bool((pay_entity.get("properties") or {}).get("description")))

    if args.live and not args.routing_only:
        post_architect(args.runner)
    else:
        print("Routing-only: tickets upserted. Start the runner and re-run with --live to call Architect.")
        print("Scorecard-fail path: workflow agentic_sdlc_plan marks FACTORY-FAIL Failed when description is empty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
