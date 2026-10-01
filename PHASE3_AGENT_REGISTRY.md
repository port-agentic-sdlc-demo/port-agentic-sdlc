# Phase 3: Port AI Agent Registry & MCP Integration

Model your local agents as first-class Port entities using Port's Agent Registry pattern.

## Overview

Instead of webhooks and custom endpoints, agents are now:
- **Registered in Port** as `aiAgent` entities (Architect, Developer, Reviewer)
- **Connected to Services** via relations (which agents support which services)
- **Query Port via MCP Server** (cleaner, more secure than direct API)

## Architecture

```
Port Catalog
├── Service (auth-service, notification-service, payment-service)
├── AI Agent (architect-agent, developer-agent, reviewer-agent)
└── Relations
    ├── aiAgent → supported_services (many-to-many)
    └── jiraIssue → assigned_agent (many-to-one, future)
```

## Step 1: Import AI Agent Blueprint

```bash
export PORT_API_TOKEN="your-token"
export PORT_BASE_URL="https://api.us.getport.io"

curl -X POST $PORT_BASE_URL/v1/blueprints \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @blueprints/aiAgent.json
```

## Step 2: Register Agent Entities

Import the three agents:

```bash
# Register Architect Agent
curl -X POST $PORT_BASE_URL/v1/blueprints/aiAgent/entities \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @blueprints/entities/architect-agent.json

# Register Developer Agent
curl -X POST $PORT_BASE_URL/v1/blueprints/aiAgent/entities \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @blueprints/entities/developer-agent.json

# Register Reviewer Agent
curl -X POST $PORT_BASE_URL/v1/blueprints/aiAgent/entities \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @blueprints/entities/reviewer-agent.json
```

Verify in Port UI:
1. Navigate to **Data Model → AI Agent**
2. You should see three agent entities

## Step 3: Update Service Blueprint (Add Relations)

Update the Service blueprint to relate to agents:

```json
{
  "identifier": "service",
  "title": "Service",
  "schema": {
    ...existing properties...
  },
  "relations": {
    "managed_by_agents": {
      "title": "Managed By Agents",
      "target": "aiAgent",
      "required": false,
      "many": true
    }
  }
}
```

## Step 4: Configure Port MCP Server

Port provides an MCP (Model Context Protocol) server that agents can query securely:

### For Local Agents (Localhost)

Add to your agent's environment:

```bash
# .env
PORT_MCP_URL=https://mcp.us.getport.io/v1
PORT_MCP_TOKEN=your-port-api-token
```

### For Agents in Claude Code/Cursor

The MCP server endpoint:
```
https://mcp.us.getport.io/v1  (US)
https://mcp.port.io/v1         (EU)
```

## Step 5: Update Agents to Use MCP

Replace direct Port API calls with MCP queries.

**Before (Direct API):**
```python
response = requests.get(
    f"{port_base_url}/v1/blueprints/service/entities",
    headers={"Authorization": f"Bearer {token}"}
)
```

**After (MCP):**
```python
# Agent makes natural language query via MCP
# "List all services that this agent supports"
# "Get architectural patterns from the catalog"
# "Find the auth-service entity and its dependencies"
```

## Benefits of This Approach

✅ **Agents are first-class Port entities** - visible in catalog  
✅ **Proper relations** - traceability between agents, services, issues  
✅ **MCP Server** - cleaner, more secure agent interface  
✅ **Natural language** - agents query catalog naturally  
✅ **Read-only mode** - restrict agent permissions if needed  
✅ **No webhooks** - simpler architecture  

## Next Steps

1. ✅ Create aiAgent blueprint
2. ✅ Register three agents
3. ⏳ Update Service blueprint with relations
4. ⏳ Integrate Port MCP Server into agents
5. ⏳ Implement natural language queries
6. ⏳ Update actions to trigger proper agents
7. ⏳ Model Jira integration (jira_issue blueprint)

## Resources

- [Port AI Agent Registry](https://docs.port.io/agent-management/ai-registry/agent-registry/)
- [Port MCP Server Installation](https://docs.port.io/agent-management/port-mcp-server/installation/)
- [Port Data Model Setup](https://docs.port.io/guides/all/build-ai-agent-registry/#set-up-data-model)
