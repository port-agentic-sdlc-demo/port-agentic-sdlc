# Webhook Handler - Port Integration Layer

The webhook handler receives Port self-service action triggers and orchestrates agents to complete them.

## Architecture

```
Port UI
  ↓
User clicks "Design Service" button
  ↓
Port sends webhook POST /webhook/action
  ↓
Webhook Handler (FastAPI)
  ↓
Routes to appropriate agent
  ↓
Agent runs in background
  ↓
Agent calls Port API to update action status
  ↓
Port UI shows results
```

## Running Locally

### 1. Start the Webhook Handler

```bash
# Make sure .env is configured with Port credentials
python run_webhook.py
```

You should see:
```
📡 Listening on http://localhost:8000
🔗 POST /webhook/action - receive Port actions
📊 GET /webhook/status/{action_run_id} - check action status
```

### 2. Test with Simulated Port Webhook

In another terminal:
```bash
python test_webhook.py
```

This simulates Port sending webhook calls and checks the results.

## API Endpoints

### POST /webhook/action
Receive a Port self-service action trigger.

**Request:**
```json
{
  "action_run_id": "run_12345",
  "action_id": "design_service",
  "blueprint": "service",
  "entity_id": "new-feature",
  "trigger": "ui_button",
  "input_data": {
    "feature_name": "User Profile Service",
    "requirements": "..."
  },
  "port_url": "https://app.us.port.io"
}
```

**Response:**
```json
{
  "ok": true,
  "action_run_id": "run_12345",
  "message": "Action queued for processing"
}
```

### GET /webhook/status/{action_run_id}
Check the status of a running action.

**Response:**
```json
{
  "action_id": "design_service",
  "entity_id": "new-feature",
  "status": "running|success|failure",
  "summary": "Architecture design completed",
  "output": { "design": "..." },
  "error": null,
  "started_at": "2026-10-01T...",
  "completed_at": "2026-10-01T..."
}
```

## Agent Task Types

### ArchitectTask (design_service, architect)
Triggers Architect Agent to design a new service.

**Input fields:**
- `feature_name`: Name of the service to design
- `requirements`: Requirements and constraints

**Output:**
- `design`: Architecture recommendation

### DeveloperTask (implement_feature, developer)
Triggers Developer Agent to implement a feature.

**Input fields:**
- `jira_ticket`: Jira ticket description
- `architecture`: Approved architecture design

**Output:**
- `implementation`: Code and PR details

### ReviewerTask (review_pr, reviewer)
Triggers Reviewer Agent to review a pull request.

**Input fields:**
- `pr_url`: GitHub PR URL

**Output:**
- `review`: Code review findings

## Action Routing

Actions are routed to agents based on `action_id`:

| action_id | Agent | Purpose |
|---|---|---|
| `design_service` | Architect | Design new service architecture |
| `architect` | Architect | Same as above |
| `implement_feature` | Developer | Implement a feature |
| `developer` | Developer | Same as above |
| `review_pr` | Reviewer | Review pull request |
| `reviewer` | Reviewer | Same as above |

## Running in Production

For production deployment:

1. **Use a real database** instead of in-memory store
   - Store action results in PostgreSQL
   - Persist agent outputs
   - Track audit trail

2. **Add authentication**
   - Verify webhook signature from Port
   - API key for status endpoint

3. **Deploy as a service**
   - Docker container
   - Running on a server accessible from Port
   - HTTPS endpoint

4. **Configure Port webhook**
   - Self-service action settings
   - Point to your webhook URL
   - Add required input fields

## Webhook Flow Example

### 1. Port Self-Service Action Setup
In Port, create action:
- **Name**: "Design New Service"
- **Blueprint**: service
- **Webhook URL**: `https://your-server.com/webhook/action`
- **Input Fields**: 
  - `feature_name` (text)
  - `requirements` (textarea)

### 2. User Clicks Button in Port
User in Port UI clicks "Design New Service" on a service entity.

### 3. Port Sends Webhook
Port calls: `POST /webhook/action`
```json
{
  "action_run_id": "run_abc123",
  "action_id": "design_service",
  "blueprint": "service",
  "entity_id": "service-xyz",
  "input_data": {
    "feature_name": "User Profile Service",
    "requirements": "..."
  }
}
```

### 4. Webhook Handler Receives & Responds
- Returns immediately (202 Accepted)
- Spawns Architect Agent in background
- Stores action metadata

### 5. Agent Runs Asynchronously
- Architect Agent queries Port for existing services
- Designs architecture
- Returns results

### 6. Port Polls for Status
Port (or user) polls: `GET /webhook/status/run_abc123`

Gets back:
```json
{
  "status": "success",
  "summary": "Architecture design completed",
  "output": { "design": "..." }
}
```

### 7. Port UI Updates
Port shows the design results in the UI.

## Troubleshooting

**"Cannot connect to localhost:8000"**
- Make sure webhook handler is running: `python run_webhook.py`

**"Agent not executing"**
- Check `.env` has `ANTHROPIC_API_KEY` set
- Check logs in webhook handler output

**"Port webhook not reaching handler"**
- If using localhost, Port cloud can't reach it
- Deploy handler to internet-accessible server
- Use ngrok for local testing: `ngrok http 8000`

## Next Steps

1. ✅ Webhook handler scaffolded (done)
2. ⏳ Create Port self-service action definitions
3. ⏳ Deploy handler to public URL
4. ⏳ Configure Port to send webhooks
5. ⏳ End-to-end testing
