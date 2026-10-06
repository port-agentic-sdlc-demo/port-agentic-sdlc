"""Port REST client used by local factory agents."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import requests


class PortAPIClient:
    """Client for Port's REST API."""

    def __init__(self, base_url: str = None, api_token: str = None):
        self.base_url = (base_url or os.getenv("PORT_BASE_URL") or "https://api.us.getport.io").rstrip("/")
        self.api_token = api_token or self._token_from_client_credentials() or os.getenv("PORT_API_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.api_token}" if self.api_token else "",
            "Content-Type": "application/json",
        }

    def _token_from_client_credentials(self) -> Optional[str]:
        client_id = os.getenv("PORT_CLIENT_ID")
        client_secret = os.getenv("PORT_CLIENT_SECRET")
        if not client_id or not client_secret:
            return None
        try:
            response = requests.post(
                f"{self.base_url}/v1/auth/access_token",
                json={"clientId": client_id, "clientSecret": client_secret},
                timeout=15,
            )
            response.raise_for_status()
            return response.json().get("accessToken") or response.json().get("access_token")
        except Exception:
            return None

    def get_entity(self, entity_id: str, blueprint: str = "service") -> Dict[str, Any]:
        try:
            endpoint = f"{self.base_url}/v1/blueprints/{blueprint}/entities/{entity_id}"
            response = requests.get(endpoint, headers=self.headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get("entity") or data
            return {"error": f"HTTP {response.status_code}", "body": response.text, "entity_id": entity_id}
        except Exception as exc:
            return {"error": str(exc), "entity_id": entity_id}

    def search_entities(self, blueprint: str, filter_query: str = None) -> List[Dict[str, Any]]:
        try:
            endpoint = f"{self.base_url}/v1/blueprints/{blueprint}/entities"
            response = requests.get(endpoint, headers=self.headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            entities = data.get("entities", [])
            if filter_query:
                needle = filter_query.lower()
                entities = [e for e in entities if needle in json.dumps(e).lower()]
            return entities
        except Exception as exc:
            return [{"error": str(exc)}]

    def get_service_dependencies(self, service_id: str) -> Dict[str, Any]:
        entity = self.get_entity(service_id, blueprint="service")
        if "error" in entity:
            return entity
        properties = entity.get("properties", {})
        return {
            "service_id": service_id,
            "path": properties.get("path"),
            "dependencies": properties.get("dependencies", []),
            "tech_stack": properties.get("tech_stack") or properties.get("techStack", []),
            "owner": properties.get("owner", "unassigned"),
            "serviceTier": properties.get("serviceTier"),
            "repository_url": properties.get("repository_url"),
            "github_repository_id": properties.get("github_repository_id"),
        }

    def upsert_entity(
        self,
        blueprint: str,
        identifier: str,
        properties: Dict[str, Any] = None,
        relations: Dict[str, Any] = None,
        title: str = None,
    ) -> Dict[str, Any]:
        try:
            endpoint = f"{self.base_url}/v1/blueprints/{blueprint}/entities"
            payload: Dict[str, Any] = {"identifier": identifier, "properties": properties or {}}
            if title:
                payload["title"] = title
            if relations:
                payload["relations"] = relations
            response = requests.post(
                endpoint,
                json=payload,
                headers=self.headers,
                params={"upsert": "true", "merge": "true"},
                timeout=20,
            )
            if response.status_code >= 400:
                return {"error": f"HTTP {response.status_code}", "body": response.text}
            return {"success": True, "response": response.json()}
        except Exception as exc:
            return {"error": str(exc)}

    def trigger_action(self, action_id: str, entity_id: str, input_data: Dict = None) -> Dict[str, Any]:
        try:
            endpoint = f"{self.base_url}/v1/actions/{action_id}/runs"
            payload = {"entity": entity_id, "properties": input_data or {}}
            response = requests.post(endpoint, json=payload, headers=self.headers, timeout=15)
            response.raise_for_status()
            return {"success": True, "action_id": action_id, "response": response.json()}
        except Exception as exc:
            return {"error": str(exc), "action_id": action_id}

    def update_action_status(
        self, action_run_id: str, status: str, summary: str = "", link: str = ""
    ) -> Dict[str, Any]:
        try:
            endpoint = f"{self.base_url}/v1/actions/runs/{action_run_id}/status"
            payload = {"status": status, "summary": summary, "link": link}
            response = requests.patch(endpoint, json=payload, headers=self.headers, timeout=15)
            response.raise_for_status()
            return {"success": True, "action_run_id": action_run_id}
        except Exception as exc:
            return {"error": str(exc), "action_run_id": action_run_id}


def create_port_tools(port_client: PortAPIClient = None) -> List[Dict]:
    return [
        {
            "name": "port_get_entity",
            "description": "Fetch a service, jiraIssue, or other entity from Port's catalog",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "Entity identifier"},
                    "blueprint": {
                        "type": "string",
                        "description": "Blueprint identifier (service, jiraIssue, githubPullRequest)",
                    },
                },
                "required": ["entity_id"],
            },
        },
        {
            "name": "port_search_entities",
            "description": "Search entities by blueprint type in Port",
            "input_schema": {
                "type": "object",
                "properties": {
                    "blueprint": {"type": "string"},
                    "filter_query": {"type": "string", "description": "Optional substring filter"},
                },
                "required": ["blueprint"],
            },
        },
        {
            "name": "port_get_service_dependencies",
            "description": "Get dependencies, path, tier, and tech stack for a service",
            "input_schema": {
                "type": "object",
                "properties": {"service_id": {"type": "string"}},
                "required": ["service_id"],
            },
        },
        {
            "name": "port_upsert_entity",
            "description": "Create or merge a Port entity (use to write factoryStage, architectureSpec, prUrl)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "blueprint": {"type": "string"},
                    "identifier": {"type": "string"},
                    "title": {"type": "string"},
                    "properties_json": {
                        "type": "string",
                        "description": "JSON object of properties to merge",
                    },
                    "relations_json": {
                        "type": "string",
                        "description": "JSON object of relations to merge",
                    },
                },
                "required": ["blueprint", "identifier"],
            },
        },
    ]


def handle_port_tool_call(tool_name: str, tool_input: Dict, port_client: PortAPIClient = None) -> str:
    if port_client is None:
        port_client = PortAPIClient()

    if tool_name == "port_get_entity":
        result = port_client.get_entity(tool_input["entity_id"], tool_input.get("blueprint") or "service")
    elif tool_name == "port_search_entities":
        result = port_client.search_entities(tool_input["blueprint"], tool_input.get("filter_query"))
    elif tool_name == "port_get_service_dependencies":
        result = port_client.get_service_dependencies(tool_input["service_id"])
    elif tool_name == "port_upsert_entity":
        properties = json.loads(tool_input.get("properties_json") or "{}")
        relations = json.loads(tool_input.get("relations_json") or "{}") or None
        result = port_client.upsert_entity(
            tool_input["blueprint"],
            tool_input["identifier"],
            properties=properties,
            relations=relations,
            title=tool_input.get("title"),
        )
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
