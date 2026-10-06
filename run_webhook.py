#!/usr/bin/env python3
"""Run the webhook handler for local testing."""

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    print("Starting Agentic SDLC Factory Runner...")
    print("Listening on http://localhost:8000")
    print("POST /factory/architect|developer|reviewer")
    print("POST /webhook/action (classic actions)")
    print("GET  /webhook/status/{run_id}")

    uvicorn.run(
        "agents.webhook_handler:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
