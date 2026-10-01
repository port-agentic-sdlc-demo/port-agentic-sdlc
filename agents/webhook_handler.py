"""Webhook handler for Port self-service actions.

Receives action triggers from Port and spawns appropriate agents.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, ValidationError
from typing import Optional, Dict, Any
import json
import uuid
from datetime import datetime
import asyncio
import os
import requests

from agents import ArchitectAgent, DeveloperAgent, ReviewerAgent

app = FastAPI(
    title="Agentic SDLC Webhook Handler",
    description="Receives Port self-service actions and orchestrates agents",
    version="1.0.0"
)

# In-memory store for action results (use database in production)
action_results = {}


# Models
class ActionInput(BaseModel):
    """Input from a Port self-service action."""
    action_id: str
    run_id: str
    entity_id: str
    trigger: str
    input_data: Dict[str, Any]


class WebhookPayload(BaseModel):
    """Port webhook payload."""
    action_run_id: str
    action_id: str
    blueprint: str
    entity_id: str
    trigger: str
    input_data: Dict[str, Any]
    port_url: str = "https://app.us.port.io"


class ActionResult(BaseModel):
    """Result of an action execution."""
    action_run_id: str
    status: str  # "running", "success", "failure"
    summary: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "agentic-sdlc-webhook-handler"}


@app.post("/webhook/action")
async def handle_action(request: Request):
    """
    Handle Port self-service action trigger.

    Accepts webhook from Port, spawns appropriate agent in background,
    and returns immediately while agent runs asynchronously.
    """
    # Extract query parameters from URL
    action_run_id = request.query_params.get("action_run_id")
    action_id = request.query_params.get("action_id")
    blueprint = request.query_params.get("blueprint", "service")
    entity_id = request.query_params.get("entity_id")
    trigger = request.query_params.get("trigger", "self-service")

    print(f"\n[Webhook] ===== NEW REQUEST =====")
    print(f"[Webhook] Headers: {dict(request.headers)}")
    print(f"[Webhook] action_run_id: {action_run_id}")
    print(f"[Webhook] action_id: {action_id}")
    print(f"[Webhook] entity_id: {entity_id}")

    # Port template vars aren't expanding, so generate our own action_run_id
    if not action_run_id or action_run_id == "null":
        action_run_id = str(uuid.uuid4())
        print(f"[Webhook] Generated action_run_id: {action_run_id}")

    if not action_id or action_id == "null":
        action_id = "design_service"  # Default

    if not entity_id or entity_id == "null":
        entity_id = "unknown"  # Default

    # Fetch action input from Port API (may return empty if action_run_id was generated)
    port_token = os.getenv("PORT_API_TOKEN")
    port_base_url = os.getenv("PORT_BASE_URL", "https://api.getport.io")
    input_data = await _fetch_action_input(action_run_id, port_base_url, port_token)

    # Build payload with valid values
    payload = WebhookPayload(
        action_run_id=action_run_id,
        action_id=action_id,
        blueprint=blueprint,
        entity_id=entity_id,
        trigger=trigger,
        input_data=input_data
    )

    print(f"[Webhook] input_data: {payload.input_data}")

    # Store action metadata
    action_results[action_run_id] = {
        "action_id": action_id,
        "entity_id": payload.entity_id,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "summary": "Agent is processing your request...",
    }

    # Route to appropriate agent based on action_id
    agent_task = _route_to_agent(action_id, payload)

    # Run agent synchronously (Port waits for response)
    await _execute_agent(action_run_id, agent_task, payload)

    # Return final result
    result = action_results.get(action_run_id, {})
    return {
        "ok": True,
        "action_run_id": action_run_id,
        "status": result.get("status", "success"),
        "summary": result.get("summary", "Action completed"),
        "output": result.get("output", {}),
    }


@app.get("/webhook/status/{action_run_id}")
async def get_action_status(action_run_id: str):
    """Check the status of a running action."""
    if action_run_id not in action_results:
        raise HTTPException(status_code=404, detail="Action not found")
    return action_results[action_run_id]


# Agent Task Types
class AgentTask:
    """Base class for agent tasks."""
    def __init__(self, action_run_id: str, payload: WebhookPayload):
        self.action_run_id = action_run_id
        self.payload = payload

    async def execute(self) -> ActionResult:
        raise NotImplementedError


class ArchitectTask(AgentTask):
    """Task for Architect Agent."""
    async def execute(self) -> ActionResult:
        agent = ArchitectAgent()
        user_input = self._build_prompt()
        try:
            response = agent.run(user_input, max_iterations=10)
            return ActionResult(
                action_run_id=self.action_run_id,
                status="success",
                summary="Architecture design completed",
                output={"design": response}
            )
        except Exception as e:
            return ActionResult(
                action_run_id=self.action_run_id,
                status="failure",
                summary="Architecture design failed",
                error=str(e)
            )

    def _build_prompt(self) -> str:
        """Build prompt for Architect Agent from Port input."""
        input_data = self.payload.input_data
        feature_name = input_data.get("feature_name", "New Feature")
        requirements = input_data.get("requirements", "")

        prompt = f"""
You are designing architecture for: {feature_name}

Requirements:
{requirements}

Query Port to understand existing services, their tech stacks, and patterns.
Then provide a recommended architecture that integrates with existing services.
"""
        return prompt.strip()


class DeveloperTask(AgentTask):
    """Task for Developer Agent."""
    async def execute(self) -> ActionResult:
        agent = DeveloperAgent()
        user_input = self._build_prompt()
        try:
            response = agent.run(user_input, max_iterations=10)
            return ActionResult(
                action_run_id=self.action_run_id,
                status="success",
                summary="Implementation completed - PR created",
                output={"implementation": response}
            )
        except Exception as e:
            return ActionResult(
                action_run_id=self.action_run_id,
                status="failure",
                summary="Implementation failed",
                error=str(e)
            )

    def _build_prompt(self) -> str:
        """Build prompt for Developer Agent from Port input."""
        input_data = self.payload.input_data
        jira_ticket = input_data.get("jira_ticket", "")
        architecture = input_data.get("architecture", "")

        prompt = f"""
You are implementing a feature from Jira ticket:
{jira_ticket}

Approved Architecture:
{architecture}

Query Port to understand the relevant services and their patterns.
Then implement the feature following the approved architecture.
Create a pull request with the implementation.
"""
        return prompt.strip()


class ReviewerTask(AgentTask):
    """Task for Reviewer Agent."""
    async def execute(self) -> ActionResult:
        agent = ReviewerAgent()
        user_input = self._build_prompt()
        try:
            response = agent.run(user_input, max_iterations=10)
            return ActionResult(
                action_run_id=self.action_run_id,
                status="success",
                summary="Code review completed",
                output={"review": response}
            )
        except Exception as e:
            return ActionResult(
                action_run_id=self.action_run_id,
                status="failure",
                summary="Code review failed",
                error=str(e)
            )

    def _build_prompt(self) -> str:
        """Build prompt for Reviewer Agent from Port input."""
        input_data = self.payload.input_data
        pr_url = input_data.get("pr_url", "")

        prompt = f"""
Review the pull request at: {pr_url}

Check for:
- Security vulnerabilities
- Code quality and style
- Performance issues
- Test coverage
- Alignment with organizational standards

Provide detailed findings and recommendations.
"""
        return prompt.strip()


# Helper Functions
async def _fetch_action_input(run_id: str, port_base_url: str, port_token: str) -> Dict[str, Any]:
    """Fetch action input from Port API using action run ID."""
    if not port_token:
        print(f"[Webhook] No PORT_API_TOKEN set, skipping Port API call")
        return {}

    try:
        # Call Port API to get action run details
        url = f"{port_base_url}/v1/actions/runs/{run_id}"
        headers = {"Authorization": f"Bearer {port_token}"}
        response = requests.get(url, headers=headers, timeout=10)

        print(f"[Webhook] Port API call: {url} -> {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            run_data = data.get("run", {})
            input_data = run_data.get("input", {})
            print(f"[Webhook] Fetched input from Port: {input_data}")
            return input_data
        else:
            print(f"[Webhook] Port API error: {response.status_code}")
            return {}
    except Exception as e:
        print(f"[Webhook] Error fetching action details: {str(e)}")
        return {"input": {}, "blueprint": "service"}


def _route_to_agent(action_id: str, payload: WebhookPayload) -> AgentTask:
    """Route action to appropriate agent task based on action_id."""
    action_map = {
        "design_service": ArchitectTask,
        "architect": ArchitectTask,
        "implement_feature": DeveloperTask,
        "developer": DeveloperTask,
        "review_pr": ReviewerTask,
        "reviewer": ReviewerTask,
    }

    task_class = action_map.get(action_id.lower(), ArchitectTask)
    return task_class(payload.action_run_id, payload)


async def _execute_agent(action_run_id: str, agent_task: AgentTask, payload: WebhookPayload):
    """Execute agent task and update Port with results."""
    print(f"[Webhook] Executing action: {action_run_id}")

    try:
        # Run the agent
        result = await agent_task.execute()

        # Check if agent output contains critical errors
        detected_status = _detect_actual_status(result)
        detected_issues = _extract_error_messages(result)

        # Store result with detected status
        action_results[action_run_id] = {
            "action_id": payload.action_id,
            "entity_id": payload.entity_id,
            "status": detected_status,
            "summary": result.summary,
            "output": result.output,
            "error": result.error,
            "completed_at": datetime.now().isoformat(),
            "detected_issues": detected_issues,
        }

        # Report back to Port
        await _report_to_port(payload, result)

        print(f"[Webhook] Action {action_run_id} completed with status: {detected_status}")
        if detected_issues:
            print(f"[Webhook] Issues detected: {detected_issues}")

    except Exception as e:
        print(f"[Webhook] Error executing action {action_run_id}: {str(e)}")
        action_results[action_run_id].update({
            "status": "failure",
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
        })


async def _report_to_port(payload: WebhookPayload, result: ActionResult):
    """Report action result back to Port."""
    print(f"[Webhook] Reporting to Port: {result.action_run_id} = {result.status}")
    print(f"[Webhook] Summary: {result.summary}")

    port_token = os.getenv("PORT_API_TOKEN")
    port_base_url = os.getenv("PORT_BASE_URL", "https://api.getport.io")

    if not port_token or not result.action_run_id:
        print(f"[Webhook] Skipping Port API update (missing token or action_run_id)")
        return

    try:
        # Call Port API to update action status
        url = f"{port_base_url}/v1/actions/runs/{result.action_run_id}/status"
        headers = {"Authorization": f"Bearer {port_token}", "Content-Type": "application/json"}
        body = {
            "status": result.status,
            "summary": result.summary,
            "output": result.output or {}
        }

        response = requests.patch(url, json=body, headers=headers, timeout=10)
        print(f"[Webhook] Port API status update: {url} -> {response.status_code}")

        if response.status_code not in [200, 204]:
            print(f"[Webhook] Port API error: {response.text}")
    except Exception as e:
        print(f"[Webhook] Error reporting to Port: {str(e)}")


def _detect_actual_status(result: ActionResult) -> str:
    """
    Detect actual status from agent output.

    Agents may complete "successfully" but their output shows they failed
    to access required data (e.g., 401 errors from Port).
    """
    if result.status == "failure":
        return "failure"

    output_text = ""
    if result.output:
        if isinstance(result.output, dict):
            output_text = json.dumps(result.output).lower()
        else:
            output_text = str(result.output).lower()

    summary_text = (result.summary or "").lower()

    # Check for critical errors
    critical_errors = [
        "401 unauthorized",
        "forbidden",
        "credentials",
        "blocked",
        "couldn't read",
        "couldn't access",
        "failed to access",
        "no data",
        "couldn't find",
    ]

    for error in critical_errors:
        if error in output_text or error in summary_text:
            return "partial_success"

    return "success"


def _extract_error_messages(result: ActionResult) -> list:
    """Extract error messages from agent output."""
    errors = []

    if result.error:
        errors.append(f"Exception: {result.error}")

    if result.output:
        output_text = ""
        if isinstance(result.output, dict):
            output_text = json.dumps(result.output)
        else:
            output_text = str(result.output)

        # Extract error patterns
        if "401" in output_text or "Unauthorized" in output_text:
            errors.append("Port API authentication failed (401)")
        if "404" in output_text or "not found" in output_text.lower():
            errors.append("Required data not found in Port")
        if "timeout" in output_text.lower():
            errors.append("Port API timeout")

    return errors


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
