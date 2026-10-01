"""Port MCP (Model Context Protocol) client for proper agent integration."""

import os
import json
import requests
from typing import Optional, Dict, Any


class PortMCPAuth:
    """Handle authentication with Port's MCP server."""

    def __init__(self, client_id: str = None, client_secret: str = None, base_url: str = None):
        self.client_id = client_id or os.getenv("PORT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("PORT_CLIENT_SECRET")
        self.base_url = base_url or os.getenv("PORT_MCP_URL", "https://mcp.us.port.io/v1")
        self.access_token = None
        self.token_expires_in = 0

    def get_access_token(self) -> Optional[str]:
        """Get a Bearer token from Port's MCP token endpoint."""
        if not self.client_id or not self.client_secret:
            raise ValueError("PORT_CLIENT_ID and PORT_CLIENT_SECRET must be set")

        try:
            token_endpoint = f"{self.base_url}/token"
            response = requests.post(
                token_endpoint,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.token_expires_in = data.get("expires_in", 10800)
                return self.access_token
            else:
                raise Exception(f"Failed to get token: {response.status_code} - {response.text}")

        except Exception as e:
            raise Exception(f"MCP Token error: {str(e)}")


class PortMCPClient:
    """Client for connecting to Port's MCP Server."""

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        base_url: str = None,
    ):
        self.base_url = base_url or os.getenv("PORT_MCP_URL", "https://mcp.us.port.io/v1")
        self.auth = PortMCPAuth(client_id, client_secret, self.base_url)
        self.access_token = None
        self._refresh_token()

    def _refresh_token(self):
        """Get a fresh access token."""
        self.access_token = self.auth.get_access_token()

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for MCP requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def query_catalog(self, question: str) -> str:
        """
        Query Port's catalog using the MCP server.

        This method communicates with Port's MCP server to answer natural language
        questions about the software catalog.

        Args:
            question: Natural language question about the catalog

        Returns:
            Response from Port's catalog query
        """
        try:
            # Port's MCP server provides a catalog query tool
            # We call it through the standard MCP protocol
            payload = {
                "method": "tools/call",
                "params": {
                    "name": "port_search_catalog",
                    "arguments": {
                        "query": question,
                    }
                }
            }

            response = requests.post(
                f"{self.base_url}/messages",
                json=payload,
                headers=self._get_headers(),
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("result", "No result returned")
            elif response.status_code == 401:
                # Token might have expired, refresh and retry
                self._refresh_token()
                return self.query_catalog(question)
            else:
                return f"MCP Query error: {response.status_code} - {response.text[:200]}"

        except Exception as e:
            return f"Error querying Port MCP: {str(e)}"

    def list_services(self) -> str:
        """List all services in the catalog via MCP."""
        return self.query_catalog(
            "List all services in the Port catalog with their names, descriptions, owners, and tech stacks"
        )

    def get_service_context(self, service_name: str) -> str:
        """Get full context about a service via MCP."""
        return self.query_catalog(
            f"Get detailed information about the {service_name} service including its dependencies, "
            f"tech stack, owner, status, and repository"
        )

    def get_architecture_patterns(self) -> str:
        """Get architecture patterns from existing services via MCP."""
        return self.query_catalog(
            "What are the common architectural patterns, tech stacks, deployment methods, and best practices "
            "used across all services in the catalog?"
        )


def create_mcp_tool(mcp_client: PortMCPClient):
    """Create a tool definition for Claude to use MCP queries."""
    return {
        "name": "port_catalog_query",
        "description": "Query Port's software catalog using the MCP (Model Context Protocol) server. "
        "Use this to understand services, architecture patterns, dependencies, and best practices.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Natural language question about the Port catalog "
                    "(e.g., 'What services exist?', 'What tech stacks are used?', 'What dependencies does auth-service have?')",
                }
            },
            "required": ["question"],
        },
    }


def handle_mcp_tool_call(mcp_client: PortMCPClient, tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Handle MCP tool calls from Claude."""
    if tool_name != "port_catalog_query":
        return f"Unknown tool: {tool_name}"

    question = tool_input.get("question", "")
    if not question:
        return "No question provided"

    result = mcp_client.query_catalog(question)
    return result
