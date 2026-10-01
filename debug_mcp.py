#!/usr/bin/env python3
"""Debug script to find the correct Port MCP endpoint."""

import os
from dotenv import load_dotenv
from tools.port_mcp import PortMCPClient

load_dotenv()

print("=" * 80)
print("PORT MCP ENDPOINT DEBUGGER")
print("=" * 80)

mcp_client = PortMCPClient()

print(f"\nBase URL: {mcp_client.base_url}")
print(f"API Token: {'***' + mcp_client.api_token[-10:] if mcp_client.api_token else 'NOT SET'}")

print("\nTesting different endpoint formats...\n")

results = mcp_client.debug_endpoints()
print(results)

print("\n" + "=" * 80)
print("INTERPRETATION:")
print("=" * 80)
print("""
If you see a 200 response: The endpoint is correct! We'll use that.
If you see 404s for all: The MCP endpoint path might be different.
If you see 401/403: Authentication might need to be adjusted.

Common issues:
1. The endpoint might be: /mcp/query, /catalog/query, or /tools/query
2. The base URL might be different: mcp.getport.io (without 'us') or api.getport.io
3. The header format might need "X-Port-Token" instead of "Authorization: Bearer"

What status code did you get?
""")
