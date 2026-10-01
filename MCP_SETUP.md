# Port MCP Server Setup Guide

## Overview

Agents now use Port's **MCP (Model Context Protocol) Server** to query the software catalog. This provides:
- ✅ Native MCP protocol integration (not REST hacks)
- ✅ Machine-to-machine authentication
- ✅ Natural language catalog queries
- ✅ Automatic token refresh

## Prerequisites

1. Port instance (US or EU)
2. Port API access

## Step 1: Create MCP Credentials

In your Port instance:

1. Go to **Settings → API Tokens**
2. Create a new token for **Machine-to-Machine Authentication**
3. Copy the **Client ID** and **Client Secret**

## Step 2: Configure Environment

Update `.env` with your MCP credentials:

```bash
# Port MCP Configuration
PORT_CLIENT_ID=your-client-id
PORT_CLIENT_SECRET=your-client-secret
PORT_MCP_URL=https://mcp.us.port.io/v1  # or https://mcp.port.io/v1 for EU
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs the `mcp` package needed for MCP protocol communication.

## Step 4: Test MCP Connection

Create a test script:

```python
from tools.port_mcp import PortMCPClient

client = PortMCPClient()
result = client.list_services()
print(result)
```

If successful, you'll get a list of services from Port's catalog.

## How It Works

1. **Authentication Phase**
   - Agent requests Bearer token from `https://mcp.us.port.io/v1/token`
   - Provides CLIENT_ID and CLIENT_SECRET
   - Gets access_token (valid for ~3 hours)

2. **Query Phase**
   - Agent calls `port_catalog_query` tool with natural language question
   - Questions are sent to Port's MCP server
   - MCP server interprets and queries the catalog
   - Results returned to agent

3. **Token Refresh**
   - Tokens auto-refresh if expired
   - No manual management needed

## Example Queries

```
"List all services in the catalog"
"What is the tech stack for auth-service?"
"What are the common architectural patterns?"
"Which services depend on notification-service?"
"What owner is responsible for payment-service?"
```

## Architecture

```
Agent (Architect/Developer/Reviewer)
  ↓
port_catalog_query tool
  ↓
PortMCPClient (handles auth + token refresh)
  ↓
https://mcp.us.port.io/v1 (Port's MCP Server)
  ↓
Port Software Catalog
```

## Troubleshooting

### "401 Unauthorized"
- Verify CLIENT_ID and CLIENT_SECRET are correct
- Check credentials haven't expired
- Token will auto-refresh, but credentials must be valid

### "404 Not Found"
- Verify you're using `mcp.us.port.io` (not `mcp.us.getport.io`)
- Check PORT_MCP_URL in .env

### "MCP connection failed"
- Ensure network can reach `https://mcp.us.port.io/v1`
- Check if behind corporate proxy

## Next Steps

1. Test the connection with Step 4
2. Run agents with `python main.py architect`
3. Watch agents query Port via MCP instead of direct API calls

## References

- [Port MCP Server Documentation](https://docs.port.io/agent-management/port-mcp-server/installation/)
- [Machine Authentication](https://docs.port.io/agent-management/port-mcp-server/token-based-authentication/)
