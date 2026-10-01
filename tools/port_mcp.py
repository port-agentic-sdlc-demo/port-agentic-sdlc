"""Port MCP (Model Context Protocol) client for agent integration."""

import os
import json
import requests
from typing import Optional, Dict, Any


class PortMCPClient:
    """Client for querying Port catalog via MCP Server."""

    def __init__(self, base_url: str = None, api_token: str = None):
        self.base_url = base_url or os.getenv("PORT_MCP_URL", "https://mcp.us.getport.io/v1")
        self.api_token = api_token or os.getenv("PORT_API_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def query(self, question: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Query Port catalog using natural language via MCP Server.

        Args:
            question: Natural language question about the catalog
            context: Optional context (service name, blueprint, etc.)

        Returns:
            Response from Port MCP Server
        """
        try:
            payload = {
                "query": question,
            }
            if context:
                payload["context"] = context

            # Try different endpoint formats
            endpoints = [
                f"{self.base_url}/query",           # Standard format
                f"{self.base_url}/messages",        # MCP standard
                f"{self.base_url.rsplit('/v1', 1)[0]}/catalog/query",  # Catalog endpoint
            ]

            for endpoint in endpoints:
                try:
                    response = requests.post(
                        endpoint,
                        json=payload,
                        headers=self.headers,
                        timeout=10,
                    )

                    if response.status_code == 200:
                        return response.json().get("result", "No result returned")
                    elif response.status_code != 404:
                        return f"MCP error at {endpoint}: {response.status_code} - {response.text[:200]}"
                except requests.exceptions.RequestException:
                    continue

            return f"MCP endpoints not found. Tried: {', '.join(endpoints)}"

        except Exception as e:
            return f"Error querying Port MCP: {str(e)}"

    def list_services(self) -> str:
        """List all services in the catalog."""
        return self.query("List all services in the catalog with their names, descriptions, and tech stacks")

    def get_service_context(self, service_name: str) -> str:
        """Get full context about a specific service."""
        return self.query(
            f"Get complete details about the {service_name} service including its dependencies, tech stack, owner, and status",
            context={"service": service_name}
        )

    def get_architecture_patterns(self) -> str:
        """Get architectural patterns from existing services."""
        return self.query(
            "What are the common architectural patterns used across services in this catalog? "
            "List tech stacks, deployment patterns, communication methods, and best practices observed"
        )

    def search_catalog(self, query: str) -> str:
        """Search the catalog for entities matching a query."""
        return self.query(
            f"Search the catalog for: {query}",
            context={"search_type": "general"}
        )


def create_mcp_tool(mcp_client: PortMCPClient):
    """Create a tool definition for Claude to use MCP queries."""
    return {
        "name": "port_mcp_query",
        "description": "Query Port's catalog using natural language via MCP Server. Use this for understanding services, architecture, and catalog context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Natural language question about the Port catalog (e.g., 'What services depend on auth-service?')",
                },
                "query_type": {
                    "type": "string",
                    "enum": ["list_services", "service_context", "architecture_patterns", "search", "general"],
                    "description": "Type of query to perform",
                }
            },
            "required": ["question", "query_type"],
        },
    }


    def debug_endpoints(self) -> str:
        """Test different MCP endpoint formats to find the correct one."""
        test_payload = {"query": "List all services"}
        endpoints_to_test = [
            f"{self.base_url}/query",
            f"{self.base_url}/messages",
            f"{self.base_url}/catalog",
            f"{self.base_url}/entities",
            f"{self.base_url.replace('/v1', '')}/query",
            "https://api.us.getport.io/v1/mcp/query",
        ]

        results = []
        for endpoint in endpoints_to_test:
            try:
                response = requests.post(
                    endpoint,
                    json=test_payload,
                    headers=self.headers,
                    timeout=5,
                )
                results.append(f"{endpoint}: {response.status_code}")
            except Exception as e:
                results.append(f"{endpoint}: ERROR ({str(e)[:50]})")

        return "\n".join(results)


def handle_mcp_tool_call(mcp_client: PortMCPClient, tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Handle MCP tool calls from Claude."""
    if tool_name != "port_mcp_query":
        return f"Unknown tool: {tool_name}"

    question = tool_input.get("question", "")
    query_type = tool_input.get("query_type", "general")

    if query_type == "list_services":
        result = mcp_client.list_services()
    elif query_type == "service_context":
        # Extract service name from question
        result = mcp_client.get_service_context(question)
    elif query_type == "architecture_patterns":
        result = mcp_client.get_architecture_patterns()
    elif query_type == "search":
        result = mcp_client.search_catalog(question)
    else:
        result = mcp_client.query(question)

    return result
