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
            "requirements": """
            Build a User Profile Service for the onboarding flow that:
            1. Manages user profile data and avatars
            2. Integrates with Auth Service
            3. Publishes events to Notification Service
            4. Follows existing service patterns
            """
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
            print(f"✅ Action accepted: {response.json()}")

            # Poll for status
            print(f"\n⏳ Waiting for agent to complete...")
            for i in range(30):  # Poll for up to 30 seconds
                time.sleep(1)
                status_response = requests.get(
                    f"{BASE_URL}/webhook/status/{action_run_id}",
                    timeout=5
                )

                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"  [{i}s] Status: {status['status']}")

                    if status['status'] in ['success', 'failure']:
                        print(f"\n✅ Action completed!")
                        print(f"   Summary: {status['summary']}")
                        if status.get('error'):
                            print(f"   Error: {status['error']}")
                        return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {BASE_URL}")
        print(f"   Make sure the webhook handler is running:")
        print(f"   python run_webhook.py")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

    return False


def test_developer_action():
    """Test Developer Agent via webhook."""
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
            print(f"✅ Action accepted: {response.json()}")
            print(f"⏳ Agent is processing in the background...")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    print("\n🧪 Agentic SDLC Webhook Handler Tests")
    print(f"⏰ Time: {datetime.now().isoformat()}")

    # Test 1: Architect
    test_architect_action()

    # Test 2: Developer
    test_developer_action()

    print("\n" + "="*80)
    print("✅ Tests complete!")
    print("="*80)


if __name__ == "__main__":
    main()
