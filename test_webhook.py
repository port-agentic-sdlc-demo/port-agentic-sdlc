#!/usr/bin/env python3
"""Test the webhook handler by simulating Port webhook calls."""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"


def test_architect_action():
    """Test Architect Agent via webhook."""
    print("\n" + "="*80)
    print("TEST 1: Architect Agent (Design Service)")
    print("="*80)

    action_run_id = f"run_{int(time.time())}"

    payload = {
        "action_run_id": action_run_id,
        "action_id": "design_service",
        "blueprint": "service",
        "entity_id": "new-feature",
        "trigger": "ui_button",
        "input_data": {
            "feature_name": "User Profile Service",
            "requirements": "Build a User Profile Service integrating Auth and Notification services"
        },
        "port_url": "https://app.us.port.io"
    }

    print(f"\n📤 Sending action to: POST {BASE_URL}/webhook/action")
    print(f"📋 Action Run ID: {action_run_id}")

    try:
        response = requests.post(
            f"{BASE_URL}/webhook/action",
            json=payload,
            timeout=5
        )

        if response.status_code == 200:
            print(f"✅ Action accepted")
            return _poll_for_completion(action_run_id, "architect")
        else:
            print(f"❌ Error: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {BASE_URL}")
        print(f"   Make sure webhook handler is running: python run_webhook.py")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_developer_action(architect_result: bool):
    """Test Developer Agent via webhook (only if architect succeeded)."""
    if not architect_result:
        print("\n" + "="*80)
        print("TEST 2: Developer Agent (SKIPPED - Architect failed)")
        print("="*80)
        print("⏭️  Skipping Developer test since Architect did not succeed")
        return False

    print("\n" + "="*80)
    print("TEST 2: Developer Agent (Implement Feature)")
    print("="*80)

    action_run_id = f"run_{int(time.time())}"

    payload = {
        "action_run_id": action_run_id,
        "action_id": "implement_feature",
        "blueprint": "service",
        "entity_id": "user-profile-service",
        "trigger": "ui_button",
        "input_data": {
            "jira_ticket": "ONBOARD-42: Implement User Profile Service",
            "architecture": "User Profile Service integrating Auth and Notification services"
        },
        "port_url": "https://app.us.port.io"
    }

    print(f"\n📤 Sending action to: POST {BASE_URL}/webhook/action")
    print(f"📋 Action Run ID: {action_run_id}")

    try:
        response = requests.post(
            f"{BASE_URL}/webhook/action",
            json=payload,
            timeout=5
        )

        if response.status_code == 200:
            print(f"✅ Action accepted")
            return _poll_for_completion(action_run_id, "developer")
        else:
            print(f"❌ Error: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def _poll_for_completion(action_run_id: str, agent_type: str, timeout: int = 90) -> bool:
    """Poll for action completion with timeout."""
    print(f"\n⏳ Waiting for {agent_type} agent to complete (timeout: {timeout}s)...")

    for i in range(timeout):
        time.sleep(1)
        try:
            status_response = requests.get(
                f"{BASE_URL}/webhook/status/{action_run_id}",
                timeout=10
            )

            if status_response.status_code == 200:
                status = status_response.json()
                current_status = status.get('status', 'unknown')

                # Compact progress indicator
                if i % 5 == 0:
                    print(f"  [{i+1}s] Status: {current_status}")

                if current_status in ['success', 'partial_success', 'failure']:
                    print(f"\n✅ Agent completed with status: {current_status}")
                    print(f"   Summary: {status.get('summary', 'N/A')}")

                    if status.get('detected_issues'):
                        print(f"   ⚠️  Issues detected:")
                        for issue in status['detected_issues']:
                            print(f"      - {issue}")

                    if status.get('error'):
                        print(f"   Error: {status['error']}")

                    return current_status in ['success', 'partial_success']

        except requests.exceptions.Timeout:
            if i % 10 == 0:
                print(f"  [{i+1}s] Still waiting...")
        except Exception as e:
            if i % 10 == 0:
                print(f"  [{i+1}s] Checking status...")

    print(f"\n❌ Timeout: Agent did not complete in {timeout} seconds")
    return False


def main():
    print("\n🧪 Agentic SDLC Webhook Handler Tests")
    print(f"⏰ Time: {datetime.now().isoformat()}")

    # Test 1: Architect
    architect_success = test_architect_action()

    # Test 2: Developer (only if architect succeeded)
    developer_success = test_developer_action(architect_success)

    # Summary
    print("\n" + "="*80)
    print("📊 Test Summary")
    print("="*80)
    print(f"Architect Agent: {'✅ PASSED' if architect_success else '❌ FAILED'}")
    print(f"Developer Agent: {'✅ PASSED' if developer_success else '⏭️  SKIPPED' if not architect_success else '❌ FAILED'}")
    print("="*80)


if __name__ == "__main__":
    main()
