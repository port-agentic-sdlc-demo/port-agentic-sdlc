"""Webhook handler for Port workflows and classic self-service actions."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from pydantic import BaseModel

from agents import ArchitectAgent, DeveloperAgent, ReviewerAgent
from tools.port_api import PortAPIClient

app = FastAPI(
    title="Agentic SDLC Factory Runner",
    description="Receives Port workflow webhooks and runs Architect, Developer, Reviewer agents",
    version="2.0.0",
)

action_results: Dict[str, Any] = {}


class FactoryPayload(BaseModel):
    jira_key: str
    title: str = ""
    description: str = ""
    service_id: Optional[str] = None
    service_path: Optional[str] = None
    architecture_spec: Optional[str] = None
    pr_url: Optional[str] = None
    workflow_run_id: Optional[str] = None


class ActionResult(BaseModel):
    action_run_id: str
    status: str
    summary: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def _port() -> PortAPIClient:
    return PortAPIClient()


def _payload_from_workflow(body: Dict[str, Any]) -> FactoryPayload:
    """Accept either a flat factory body or a Port workflow webhook envelope."""
    if "jira_key" in body:
        return FactoryPayload.model_validate(body)

    outputs = body.get("outputs") or body
    trigger = outputs.get("trigger") or body.get("entity") or {}
    identifier = (
        body.get("entityIdentifier")
        or trigger.get("identifier")
        or (trigger.get("entity") or {}).get("identifier")
        or ""
    )
    properties = trigger.get("properties") or (trigger.get("entity") or {}).get("properties") or {}
    relations = trigger.get("relations") or (trigger.get("entity") or {}).get("relations") or {}
    return FactoryPayload(
        jira_key=identifier,
        title=trigger.get("title") or properties.get("summary") or identifier,
        description=properties.get("description") or "",
        service_id=relations.get("service"),
        service_path=properties.get("servicePath"),
        architecture_spec=properties.get("architectureSpec"),
        pr_url=properties.get("prUrl") or body.get("pr_url"),
        workflow_run_id=body.get("workflowRunId") or body.get("runId"),
    )


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "agentic-sdlc-factory-runner"}


@app.post("/factory/architect", status_code=202)
async def factory_architect(request: Request, background_tasks: BackgroundTasks):
    return await _enqueue("architect", request, background_tasks)


@app.post("/factory/developer", status_code=202)
async def factory_developer(request: Request, background_tasks: BackgroundTasks):
    return await _enqueue("developer", request, background_tasks)


@app.post("/factory/reviewer", status_code=202)
async def factory_reviewer(request: Request, background_tasks: BackgroundTasks):
    return await _enqueue("reviewer", request, background_tasks)


@app.post("/webhook/action", status_code=202)
async def handle_action(request: Request, background_tasks: BackgroundTasks):
    """Classic Port action compatibility. Prefer /factory/{role} for workflows."""
    action_id = (request.query_params.get("action_id") or "unknown").lower()
    role_map = {
        "design_service": "architect",
        "architect": "architect",
        "implement_feature": "developer",
        "developer": "developer",
        "review_code": "reviewer",
        "review_pr": "reviewer",
        "reviewer": "reviewer",
    }
    if action_id not in role_map:
        raise HTTPException(status_code=400, detail=f"Unknown action_id {action_id}; refusing default Architect routing")
    return await _enqueue(role_map[action_id], request, background_tasks)


@app.get("/webhook/status/{run_id}")
async def get_action_status(run_id: str):
    if run_id not in action_results:
        raise HTTPException(status_code=404, detail="Run not found")
    return action_results[run_id]


async def _enqueue(role: str, request: Request, background_tasks: BackgroundTasks):
    raw = {}
    try:
        raw = await request.json()
    except Exception:
        raw = {}
    try:
        payload = _payload_from_workflow(raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_id = payload.workflow_run_id or request.query_params.get("action_run_id") or str(uuid.uuid4())
    action_results[run_id] = {
        "role": role,
        "jira_key": payload.jira_key,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    background_tasks.add_task(_execute_role, role, run_id, payload)
    return {
        "ok": True,
        "accepted": True,
        "role": role,
        "run_id": run_id,
        "jira_key": payload.jira_key,
        "status_url": f"/webhook/status/{run_id}",
    }


def _execute_role(role: str, run_id: str, payload: FactoryPayload):
    port = _port()
    try:
        if payload.jira_key:
            stage = {"architect": "Plan", "developer": "Build", "reviewer": "Review"}[role]
            port.upsert_entity("jiraIssue", payload.jira_key, properties={"factoryStage": stage})

        if role == "architect":
            prompt = _architect_prompt(payload)
            response = ArchitectAgent().run(prompt)
        elif role == "developer":
            prompt = _developer_prompt(payload)
            response = DeveloperAgent().run(prompt)
        elif role == "reviewer":
            prompt = _reviewer_prompt(payload)
            response = ReviewerAgent().run(prompt)
        else:
            raise ValueError(role)

        action_results[run_id].update(
            {
                "status": "success",
                "summary": f"{role} completed",
                "output": {"response": response},
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:
        action_results[run_id].update(
            {
                "status": "failure",
                "error": str(exc),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        if payload.jira_key:
            port.upsert_entity(
                "jiraIssue",
                payload.jira_key,
                properties={"factoryStage": "Failed", "aiReadinessReason": str(exc)},
            )


def _architect_prompt(payload: FactoryPayload) -> str:
    return f"""
Jira key: {payload.jira_key}
Title: {payload.title}
Description:
{payload.description}

Related service id (may be empty): {payload.service_id or ""}
Related service path (may be empty): {payload.service_path or ""}

Query Port, produce the architecture JSON, and upsert it onto jiraIssue {payload.jira_key}.
""".strip()


def _developer_prompt(payload: FactoryPayload) -> str:
    service_path = payload.service_path or (
        f"services/{payload.service_id}" if payload.service_id else "services/payment-service"
    )
    return f"""
Jira key: {payload.jira_key}
Service id: {payload.service_id or "payment-service"}
Service path (allowed_prefix): {service_path}

Approved architecture:
{payload.architecture_spec or ""}

Implement the change, open a PR titled with {payload.jira_key}, and upsert prUrl onto jiraIssue {payload.jira_key}.
""".strip()


def _reviewer_prompt(payload: FactoryPayload) -> str:
    return f"""
Jira key: {payload.jira_key}
PR URL: {payload.pr_url}
Expected service path: {payload.service_path or ""}

Review the PR, submit GitHub feedback, and upsert reviewVerdict onto jiraIssue {payload.jira_key}.
""".strip()
