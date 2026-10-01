#!/usr/bin/env python3
"""Run the webhook handler for local testing."""

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    print("Starting Agentic SDLC Webhook Handler...")
    print("📡 Listening on http://localhost:8000")
    print("🔗 POST /webhook/action - receive Port actions")
    print("📊 GET /webhook/status/{action_run_id} - check action status")
    print("\nReady to receive Port webhooks!")

    uvicorn.run(
        "agents.webhook_handler:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
