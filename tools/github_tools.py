"""Claude tool definitions for GitHub factory operations."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from tools.github_api import GitHubClient


def create_github_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "github_create_branch",
            "description": "Create a feature branch from the default branch",
            "input_schema": {
                "type": "object",
                "properties": {
                    "branch": {"type": "string"},
                    "from_branch": {"type": "string"},
                },
                "required": ["branch"],
            },
        },
        {
            "name": "github_get_file",
            "description": "Read a file from the GitHub repository",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "ref": {"type": "string"},
                },
                "required": ["path"],
            },
        },
        {
            "name": "github_put_file",
            "description": "Create or update a file on a branch. Path must stay under the allowed service directory.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "message": {"type": "string"},
                    "branch": {"type": "string"},
                    "allowed_prefix": {
                        "type": "string",
                        "description": "Required prefix such as services/payment-service",
                    },
                },
                "required": ["path", "content", "message", "branch", "allowed_prefix"],
            },
        },
        {
            "name": "github_create_pull_request",
            "description": "Open a pull request from a feature branch",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "head": {"type": "string"},
                    "base": {"type": "string"},
                },
                "required": ["title", "body", "head"],
            },
        },
        {
            "name": "github_list_pr_files",
            "description": "List files and patches in a pull request",
            "input_schema": {
                "type": "object",
                "properties": {"pr_url": {"type": "string"}},
                "required": ["pr_url"],
            },
        },
        {
            "name": "github_comment_on_pr",
            "description": "Post a comment on a pull request",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pr_url": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["pr_url", "body"],
            },
        },
        {
            "name": "github_submit_review",
            "description": "Submit a GitHub review: APPROVE, REQUEST_CHANGES, or COMMENT",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pr_url": {"type": "string"},
                    "body": {"type": "string"},
                    "event": {"type": "string", "enum": ["APPROVE", "REQUEST_CHANGES", "COMMENT"]},
                },
                "required": ["pr_url", "body", "event"],
            },
        },
    ]


def handle_github_tool_call(tool_name: str, tool_input: Dict[str, Any], client: GitHubClient = None) -> str:
    client = client or GitHubClient()
    try:
        if tool_name == "github_create_branch":
            result = client.create_branch(tool_input["branch"], tool_input.get("from_branch"))
        elif tool_name == "github_get_file":
            result = client.get_file(tool_input["path"], tool_input.get("ref"))
        elif tool_name == "github_put_file":
            result = client.put_file(
                tool_input["path"],
                tool_input["content"],
                tool_input["message"],
                tool_input["branch"],
                tool_input["allowed_prefix"],
            )
        elif tool_name == "github_create_pull_request":
            result = client.create_pull_request(
                tool_input["title"],
                tool_input["body"],
                tool_input["head"],
                tool_input.get("base"),
            )
        elif tool_name == "github_list_pr_files":
            result = client.list_pr_files(tool_input["pr_url"])
        elif tool_name == "github_comment_on_pr":
            result = client.create_issue_comment(tool_input["pr_url"], tool_input["body"])
        elif tool_name == "github_submit_review":
            result = client.submit_review(tool_input["pr_url"], tool_input["body"], tool_input.get("event", "COMMENT"))
        else:
            result = {"error": f"Unknown GitHub tool: {tool_name}"}
    except Exception as exc:
        result = {"error": str(exc)}
    return json.dumps(result)
