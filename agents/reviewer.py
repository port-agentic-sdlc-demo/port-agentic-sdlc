"""Reviewer Agent - reviews factory PRs and writes the verdict back to Port."""

from agents.base import BaseAgent
from tools.github_tools import create_github_tools


REVIEWER_SYSTEM_PROMPT = """You are the Security & Quality Reviewer Agent.

Workflow:
1. github_list_pr_files on the given PR URL.
2. Confirm every changed file is under the expected service path. If not, REQUEST_CHANGES.
3. Review for security, logging of secrets, error handling, and consistency with the existing FastAPI mock style.
4. github_submit_review with APPROVE, REQUEST_CHANGES, or COMMENT, plus github_comment_on_pr with a structured summary.
5. port_upsert_entity on the jiraIssue:
   - factoryStage: Done if APPROVE, Review if COMMENT, Failed if REQUEST_CHANGES for policy violations
   - reviewVerdict: approve | comment | request_changes
   - aiReadinessReason: short markdown of findings

End with JSON:
{"verdict":"approve","factoryStage":"Done","findings":["..."]}
"""


class ReviewerAgent(BaseAgent):
    def __init__(self, **kwargs):
        extra = kwargs.pop("extra_tools", None) or []
        extra = list(extra) + create_github_tools()
        super().__init__(
            name="ReviewerAgent",
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            extra_tools=extra,
            **kwargs,
        )
