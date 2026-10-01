"""Port API integration tools for agents."""

import os
import json
import requests
from typing import Any, Dict, List, Optional


class PortAPIClient:
    """Client for interacting with Port's API."""

    def __init__(self, base_url: str = None, api_token: str = None):
        self.base_url = base_url or os.getenv("PORT_BASE_URL", "https://api.getport.io")
        self.api_token = api_token or os.getenv("PORT_API_TOKEN", "demo-token")
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def get_entity(self, entity_id: str, blueprint: str = "service") -> Dict[str, Any]:
        """Fetch a single entity from Port's catalog by searching and filtering."""
        try:
            # Use search_entities and filter locally since Port's single-entity endpoint doesn't support query params
            endpoint = f"{self.base_url}/v1/blueprints/{blueprint}/entities"
            response = requests.get(endpoint, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("ok") and data.get("entities"):
                entities = data["entities"]
                # Search by identifier or name property
                for entity in entities:
                    if entity.get("identifier") == entity_id or entity.get("properties", {}).get("name") == entity_id:
                        return entity
            return {"error": "Entity not found", "entity_id": entity_id}
        except Exception as e:
            return {"error": str(e), "entity_id": entity_id}

    def search_entities(self, blueprint: str, filter_query: str = None) -> List[Dict[str, Any]]:
        """Search entities by blueprint type (e.g., 'service', 'jira-ticket')."""
        try:
            endpoint = f"{self.base_url}/v1/blueprints/{blueprint}/entities"
            response = requests.get(endpoint, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                return data.get("entities", [])
            return [{"error": "No entities found"}]
        except Exception as e:
            return [{"error": str(e)}]

    def get_service_dependencies(self, service_id: str) -> Dict[str, Any]:
        """Fetch upstream and downstream dependencies for a service."""
        try:
            entity = self.get_entity(service_id, blueprint="service")
            if "error" in entity:
                return entity
            properties = entity.get("properties", {})
            return {
                "service_id": service_id,
                "upstream_dependencies": properties.get("upstreamDependencies", []),
                "downstream_dependencies": properties.get("downstreamDependencies", []),
                "tech_stack": properties.get("techStack", []),
                "owner": properties.get("owner", "unassigned"),
            }
        except Exception as e:
            return {"error": str(e)}

    def trigger_action(self, action_id: str, entity_id: str, input_data: Dict = None) -> Dict[str, Any]:
        """Trigger a self-service action in Port."""
        try:
            endpoint = f"{self.base_url}/actions/{action_id}/trigger"
            payload = {
                "entity": entity_id,
                "input": input_data or {},
            }
            response = requests.post(endpoint, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            return {"success": True, "action_id": action_id, "response": response.json()}
        except Exception as e:
            return {"error": str(e), "action_id": action_id}

    def update_action_status(
        self, action_run_id: str, status: str, summary: str = "", link: str = ""
    ) -> Dict[str, Any]:
        """Update the status of a running action."""
        try:
            endpoint = f"{self.base_url}/action-runs/{action_run_id}"
            payload = {
                "status": status,  # 'running', 'success', 'failure'
                "summary": summary,
                "link": link,
            }
            response = requests.patch(endpoint, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            return {"success": True, "action_run_id": action_run_id}
        except Exception as e:
            return {"error": str(e), "action_run_id": action_run_id}

    def create_entity(self, blueprint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity in Port's catalog."""
        try:
            endpoint = f"{self.base_url}/entities"
            payload = {
                "blueprint": blueprint,
                "properties": data,
            }
            response = requests.post(endpoint, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            return {"success": True, "entity": response.json()}
        except Exception as e:
            return {"error": str(e)}


def create_port_tools(port_client: PortAPIClient = None) -> List[Dict]:
    """Create tool definitions for Claude to use with Port API."""
    if port_client is None:
        port_client = PortAPIClient()

    return [
        {
            "name": "port_get_entity",
            "description": "Fetch a service, ticket, or other entity from Port's software catalog",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The ID of the entity to fetch (e.g., 'payment-api', 'PAY-405')",
                    },
                    "blueprint": {
                        "type": "string",
                        "description": "Optional blueprint type (e.g., 'service', 'jira-ticket')",
                    },
                },
                "required": ["entity_id"],
            },
        },
        {
            "name": "port_search_entities",
            "description": "Search for entities by blueprint type in Port's catalog",
            "input_schema": {
                "type": "object",
                "properties": {
                    "blueprint": {
                        "type": "string",
                        "description": "Blueprint type to search (e.g., 'service', 'jira-ticket', 'database')",
                    },
                    "filter_query": {
                        "type": "string",
                        "description": "Optional filter query (e.g., 'owner:payment-team')",
                    },
                },
                "required": ["blueprint"],
            },
        },
        {
            "name": "port_get_service_dependencies",
            "description": "Get upstream and downstream dependencies for a service, including tech stack and owner",
            "input_schema": {
                "type": "object",
                "properties": {
                    "service_id": {
                        "type": "string",
                        "description": "The service ID to fetch dependencies for",
                    },
                },
                "required": ["service_id"],
            },
        },
        {
            "name": "port_trigger_action",
            "description": "Trigger a self-service action in Port",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action_id": {
                        "type": "string",
                        "description": "The action ID in Port",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "The entity to perform the action on",
                    },
                    "input_data": {
                        "type": "object",
                        "description": "Input parameters for the action",
                    },
                },
                "required": ["action_id", "entity_id"],
            },
        },
        {
            "name": "port_update_action_status",
            "description": "Update the status of an action run in Port (for reporting back progress)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action_run_id": {
                        "type": "string",
                        "description": "The action run ID to update",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["running", "success", "failure"],
                        "description": "Status to set",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Summary of the action result",
                    },
                    "link": {
                        "type": "string",
                        "description": "Link to the result (e.g., PR URL, artifact)",
                    },
                },
                "required": ["action_run_id", "status"],
            },
        },
    ]


def handle_port_tool_call(tool_name: str, tool_input: Dict, port_client: PortAPIClient = None) -> str:
    """Execute a Port API tool call and return the result."""
    if port_client is None:
        port_client = PortAPIClient()

    if tool_name == "port_get_entity":
        result = port_client.get_entity(tool_input["entity_id"], tool_input.get("blueprint"))
    elif tool_name == "port_search_entities":
        result = port_client.search_entities(tool_input["blueprint"], tool_input.get("filter_query"))
    elif tool_name == "port_get_service_dependencies":
        result = port_client.get_service_dependencies(tool_input["service_id"])
    elif tool_name == "port_trigger_action":
        result = port_client.trigger_action(
            tool_input["action_id"], tool_input["entity_id"], tool_input.get("input_data")
        )
    elif tool_name == "port_update_action_status":
        result = port_client.update_action_status(
            tool_input["action_run_id"],
            tool_input["status"],
            tool_input.get("summary", ""),
            tool_input.get("link", ""),
        )
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result)
