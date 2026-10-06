"""Developer Agent - implements the approved plan and opens a GitHub pull request."""

from agents.base import BaseAgent
from tools.github_tools import create_github_tools


DEVELOPER_SYSTEM_PROMPT = """You are the Developer Agent for an agentic software factory.

You receive a Jira key, an approved architecture spec, and a service path such as services/payment-service.

Workflow:
1. Read existing files with github_get_file (start with the service's src/main.py).
2. Create a branch named factory/<jira-key-lowercase>.
3. Apply the smallest change that satisfies the spec using github_put_file. allowed_prefix MUST be the service path. Never write outside that directory.
4. Open a PR whose title starts with the Jira key, e.g. "PAY-12 Add structured logging to process-with-retry".
5. Call port_upsert_entity on jiraIssue with properties_json:
   {"factoryStage":"Review","prUrl":"<html url>"}
6. If the GitHub client is in dry-run mode, still upsert factoryStage Build or Review with the compare URL returned.

Return a short summary including the PR URL.

Code standards for these FastAPI mocks: keep in-memory stores, add logging via the logging module, do not introduce new infrastructure.
"""


class DeveloperAgent(BaseAgent):
    def __init__(self, **kwargs):
        extra = kwargs.pop("extra_tools", None) or []
        extra = list(extra) + create_github_tools()
        super().__init__(
            name="DeveloperAgent",
            system_prompt=DEVELOPER_SYSTEM_PROMPT,
            extra_tools=extra,
            **kwargs,
        )
