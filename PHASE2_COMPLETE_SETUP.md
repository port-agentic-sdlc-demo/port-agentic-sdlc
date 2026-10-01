# Phase 2: Port Integration Layer - Complete Setup Guide

End-to-end instructions for connecting agents to Port via webhooks and self-service actions.

## Architecture Overview

```
Port Cloud
  ↓
User clicks "Design Service" button
  ↓
Port sends webhook
  ↓
ngrok tunnel
  ↓
Webhook Handler (localhost:8000)
  ↓
Routes to Agent (Architect/Developer/Reviewer)
  ↓
Agent queries Port for context
  ↓
Agent executes task
  ↓
Agent reports results back to Port
  ↓
Port UI shows results
```

---

## Prerequisites

1. ✅ Agent foundation running locally (see QUICKSTART.md)
2. ✅ Webhook handler built (agents/webhook_handler.py)
3. ✅ Action definitions created (blueprints/actions/)
4. ⏳ ngrok installed
5. ⏳ Valid Port API token

---

## Step 1: Set Up ngrok Tunnel

### Install ngrok

```bash
# macOS
brew install ngrok

# Or download from https://ngrok.com/download
```

### Start ngrok

In a new terminal:
```bash
ngrok http 8000
```

You should see:
```
Forwarding                    https://abc123-def456.ngrok-free.dev -> http://localhost:8000
```

**Copy your ngrok URL** — you'll need it next.

### Update Action URLs

The action JSON files already have ngrok URLs, but if ngrok gives you a different URL:

```bash
# Search and replace in all action files
sed -i '' 's|https://.*ngrok.*|https://your-new-ngrok-url|g' blueprints/actions/*.json
```

Or manually edit:
- `blueprints/actions/design_service.json`
- `blueprints/actions/implement_feature.json`
- `blueprints/actions/review_code.json`

Change the `invocationMethod.url` field to your ngrok URL.

---

## Step 2: Start the Webhook Handler

In another terminal:

```bash
# Activate venv
source .venv/bin/activate

# Make sure dependencies are installed
pip install -r requirements.txt

# Start webhook handler
python run_webhook.py
```

You should see:
```
📡 Listening on http://0.0.0.0:8000
🔗 POST /webhook/action - receive Port actions
📊 GET /webhook/status/{action_run_id} - check action status

Ready to receive Port webhooks!
```

---

## Step 3: Import Actions into Port

Set your Port credentials:
```bash
export PORT_API_TOKEN="your-port-api-token"
export PORT_BASE_URL="https://api.us.getport.io"
```

Import the three actions:

```bash
# Design Service action
curl -X POST $PORT_BASE_URL/v1/actions \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @blueprints/actions/design_service.json

# Implement Feature action
curl -X POST $PORT_BASE_URL/v1/actions \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @blueprints/actions/implement_feature.json

# Review Code action
curl -X POST $PORT_BASE_URL/v1/actions \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @blueprints/actions/review_code.json
```

Success response:
```json
{
  "ok": true,
  "action": {
    "identifier": "design_service",
    "title": "Design Service",
    ...
  }
}
```

---

## Step 4: Verify Actions in Port UI

1. **Open Port**: https://app.us.port.io/
2. **Navigate to Services**: Blueprint → Service
3. **Click on a service** (e.g., auth-service)
4. You should see three new buttons:
   - 🎨 **Design Service**
   - 💻 **Implement Feature**
   - ✅ **Review Code**

If you don't see them:
- Refresh the page
- Check import succeeded (run curl commands again)
- Check ngrok is still running

---

## Step 5: Test End-to-End

### Terminal Setup

You should have three terminals running:

**Terminal 1 - ngrok tunnel**:
```bash
ngrok http 8000
```

**Terminal 2 - Webhook handler**:
```bash
source .venv/bin/activate
python run_webhook.py
```

**Terminal 3 - Ready for testing**:
```bash
# Just wait here for testing
```

### Test the Flow

1. **Open Port UI**: https://app.us.port.io/

2. **Find a Service** (e.g., auth-service)

3. **Click "Design Service"** button

4. **Fill in the form**:
   - Service Name: `Test Service`
   - Requirements: `A test service to validate the flow`

5. **Watch the execution**:
   - Port shows action is running
   - Terminal 2 shows agent executing
   - Terminal 1 shows requests from Port

6. **Check results**:
   - Port UI updates with agent output
   - Or check via API: `GET http://localhost:8000/webhook/status/{action_run_id}`

### Example Result

```json
{
  "status": "partial_success",
  "summary": "Architecture design completed",
  "detected_issues": ["Port API authentication failed (401)"],
  "output": {
    "design": "# User Profile Service Architecture..."
  }
}
```

---

## Troubleshooting

### "Action button not showing in Port"

**Check:**
- Are you on a Service entity page?
- Did the curl import commands return `"ok": true`?
- Try refreshing Port UI
- Check Port settings → Actions to see if actions appear

### "Webhook times out"

**Check:**
- Is ngrok running? (`ngrok http 8000`)
- Is webhook handler running? (`python run_webhook.py`)
- Check ngrok tunnel is active (look at Terminal 1)
- Try accessing http://localhost:8000/health

### "Port API returns 401"

**Check:**
- Port API token is valid
- Token hasn't expired (regenerate if needed)
- Update .env with new token
- Agents can still run locally even if Port API fails (see graceful degradation)

### "Port can't reach webhook"

**Check:**
- ngrok shows "Online" in status
- ngrok URL matches action JSON files
- Try curl to ngrok: `curl https://your-ngrok-url/health`
- ngrok may have restarted (new URL) — update actions and re-import

### "Agent not executing"

**Check:**
- Webhook handler logs should show agent running
- Check .env has ANTHROPIC_API_KEY
- Port token is valid (for Port queries, not required for agent execution)
- Check Terminal 2 logs for errors

---

## Quick Testing Script

Alternatively, use the local test script (doesn't need Port):

```bash
python test_webhook.py
```

This simulates Port webhooks and tests the complete flow locally.

---

## Next Steps

Once end-to-end works:

1. **Deploy webhook handler to production** (AWS, Heroku, DigitalOcean)
   - Replace ngrok with production URL
   - Update actions in Port
   - Set up real database instead of in-memory store

2. **Add more blueprints** (Jira tickets, databases, APIs)
   - Create corresponding actions
   - Route to appropriate agents

3. **Enhance agent capabilities**
   - Add GitHub integration (clone, commit, open PR)
   - Add Jira integration (read tickets, update status)
   - Add Port API updates (action_run_id handling)

4. **Monitor and optimize**
   - Track action execution times
   - Monitor agent success rates
   - Collect user feedback

---

## Files Reference

| File | Purpose |
|------|---------|
| `agents/webhook_handler.py` | FastAPI webhook receiver |
| `run_webhook.py` | Startup script for webhook handler |
| `test_webhook.py` | Local testing (doesn't need Port) |
| `blueprints/actions/design_service.json` | Architect Agent action |
| `blueprints/actions/implement_feature.json` | Developer Agent action |
| `blueprints/actions/review_code.json` | Reviewer Agent action |
| `blueprints/actions/README.md` | Action configuration details |
| `WEBHOOK_HANDLER.md` | Webhook API documentation |
| `PHASE2_COMPLETE_SETUP.md` | This file |

---

## Summary

✅ Phase 2: Port Integration Layer Complete

You now have:
- Webhook handler receiving Port triggers
- Three self-service actions in Port
- End-to-end flow from Port UI → Agents → Results
- Graceful error handling and status reporting
- Local testing tools (ngrok + test_webhook.py)

Next: Deploy to production and add more integrations!
