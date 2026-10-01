# Port Self-Service Actions

Action definitions for the Agentic SDLC POC. These actions appear as buttons in the Port UI and trigger agents to execute tasks.

## Actions

### 1. Design Service (`design_service.json`)
**Triggers**: Architect Agent

**Appears on**: Service entities in Port

**Input fields**:
- `feature_name` - Name of service to design
- `requirements` - Requirements and constraints

**What it does**:
1. User clicks "Design Service" button in Port
2. Fills in service name and requirements
3. Architect Agent queries Port for existing services
4. Agent designs new service architecture
5. Results appear in Port

---

### 2. Implement Feature (`implement_feature.json`)
**Triggers**: Developer Agent

**Appears on**: Service entities in Port

**Input fields**:
- `jira_ticket` - Jira ticket ID and description
- `architecture` - Approved architecture design

**What it does**:
1. User clicks "Implement Feature" button
2. Enters Jira ticket and approved architecture
3. Developer Agent reads the ticket
4. Agent implements the feature following architecture
5. Agent opens PR and reports back

---

### 3. Review Code (`review_code.json`)
**Triggers**: Reviewer Agent

**Appears on**: Service entities in Port

**Input fields**:
- `pr_url` - GitHub PR URL

**What it does**:
1. User clicks "Review Code" button
2. Enters PR URL
3. Reviewer Agent fetches the PR
4. Agent reviews for security, quality, performance
5. Agent reports findings back to Port

---

## Setup Instructions

### Step 1: Update Webhook URL

Before importing, update the webhook URLs in all three JSON files:

Replace:
```
"url": "https://your-webhook-url.com/webhook/action"
```

With your actual webhook URL. Options:
- **Local testing**: `http://localhost:8000/webhook/action`
- **Ngrok tunnel**: `https://your-ngrok-id.ngrok.io/webhook/action`
- **Production**: `https://your-server.com/webhook/action`

### Step 2: Import Actions into Port

**Via Port API:**
```bash
# Set environment variables
export PORT_API_TOKEN="your-port-api-token"
export PORT_BASE_URL="https://api.us.getport.io"

# Import each action
curl -X POST $PORT_BASE_URL/v1/actions \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @design_service.json

curl -X POST $PORT_BASE_URL/v1/actions \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @implement_feature.json

curl -X POST $PORT_BASE_URL/v1/actions \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @review_code.json
```

**Via Port UI:**
1. Go to Settings → Actions
2. Click "Create Action"
3. Paste JSON from one of the files
4. Update webhook URL
5. Save

### Step 3: Test the Actions

1. **Start webhook handler**:
   ```bash
   python run_webhook.py
   ```

2. **Open Port UI**: https://app.us.port.io/

3. **Navigate to a Service entity**

4. **Click "Design Service"** button

5. **Fill in the form**:
   - Service Name: "User Profile Service"
   - Requirements: "A service that manages user profiles"

6. **Watch the action execute**:
   - Port shows action is running
   - Webhook handler logs agent execution
   - Results appear in Port UI

---

## Action Payload Format

When Port sends a webhook, the payload looks like:

```json
{
  "action_run_id": "run_abc123",
  "action_id": "design_service",
  "blueprint": "service",
  "entity_id": "my-service",
  "trigger": "manual",
  "input_data": {
    "feature_name": "User Profile Service",
    "requirements": "Manage user profiles and avatars"
  },
  "port_url": "https://app.us.port.io"
}
```

The webhook handler receives this and routes it to the appropriate agent.

---

## Updating Actions

If you need to update an action:

1. Edit the JSON file
2. Re-import via API (updates existing action)
3. Or update directly in Port UI

---

## Troubleshooting

**"Action button not appearing"**
- Make sure action is imported
- Check it's on the right blueprint (service)
- Refresh Port UI

**"Webhook times out"**
- Make sure webhook handler is running
- Check webhook URL is accessible from Port
- For localhost, use ngrok: `ngrok http 8000`

**"Action runs but shows error"**
- Check webhook handler logs
- Verify Port API token is valid
- Check agent can access Port data

---

## Next Steps

1. ✅ Action definitions created
2. ⏳ Import actions into Port
3. ⏳ Configure webhook URL
4. ⏳ Test actions in Port UI
5. ⏳ Deploy webhook handler to production
