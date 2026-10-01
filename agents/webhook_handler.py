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
async def handle_action(payload: WebhookPayload, background_tasks: BackgroundTasks):
    """
    Handle Port self-service action trigger.

    Accepts webhook from Port, spawns appropriate agent in background,
    and returns immediately while agent runs asynchronously.
    """
    action_run_id = payload.action_run_id
    action_id = payload.action_id

    print(f"\n[Webhook] ===== NEW REQUEST =====")
    print(f"[Webhook] action_run_id: {action_run_id}")
    print(f"[Webhook] action_id: {action_id}")
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

    # Run agent in background
    background_tasks.add_task(_execute_agent, action_run_id, agent_task, payload)

    return {
        "ok": True,
        "action_run_id": action_run_id,
        "message": "Action queued for processing",
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
async def _fetch_action_details(run_id: str, port_base_url: str, port_token: str) -> Optional[Dict[str, Any]]:
    """Fetch action details from Port API using action run ID."""
    if not port_token:
        print(f"[Webhook] No PORT_API_TOKEN set, skipping Port API call")
        return {"input": {}, "blueprint": "service"}

    try:
        # Call Port API to get action run details
        url = f"{port_base_url}/v1/actions/runs/{run_id}"
        headers = {"Authorization": f"Bearer {port_token}"}
        response = requests.get(url, headers=headers, timeout=10)

        print(f"[Webhook] Port API call: {url} -> {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            run_data = data.get("run", {})
            return {
                "input": run_data.get("input", {}),
                "blueprint": run_data.get("blueprint", "service"),
                "entity": run_data.get("entity", {})
            }
        else:
            print(f"[Webhook] Port API error: {response.text}")
            return {"input": {}, "blueprint": "service"}
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
    # This would call Port API to update action status
    # For now, just log it
    print(f"[Webhook] Reporting to Port: {result.action_run_id} = {result.status}")
    print(f"[Webhook] Summary: {result.summary}")
    if result.output:
        print(f"[Webhook] Output: {json.dumps(result.output, indent=2)}")


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
