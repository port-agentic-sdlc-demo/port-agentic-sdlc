"""Base agent implementation using the Anthropic Messages API."""

from __future__ import annotations

import os
from typing import List, Optional

from anthropic import Anthropic

from tools.github_tools import handle_github_tool_call
from tools.port_api import PortAPIClient, create_port_tools, handle_port_tool_call


class BaseAgent:
    """Base class for factory agents."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        extra_tools: Optional[List[dict]] = None,
        api_key: str = None,
        port_api_token: str = None,
        port_base_url: str = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.port_client = PortAPIClient(base_url=port_base_url, api_token=port_api_token)
        self.tools = create_port_tools(self.port_client)
        if extra_tools:
            self.tools.extend(extra_tools)
        self.conversation_history = []

    def reset(self):
        self.conversation_history = []

    def run(self, user_input: str, max_iterations: int = 12) -> str:
        self.conversation_history.append({"role": "user", "content": user_input})
        final_response = None

        for iteration in range(max_iterations):
            print(f"\n[{self.name}] Iteration {iteration + 1}/{max_iterations}", flush=True)
            response = self.client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5"),
                max_tokens=8192,
                system=self.system_prompt,
                tools=self.tools,
                messages=self.conversation_history,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if getattr(block, "type", None) == "text":
                        final_response = block.text
                self.conversation_history.append({"role": "assistant", "content": response.content})
                print(f"[{self.name}] Task completed.", flush=True)
                break

            if response.stop_reason == "tool_use":
                self.conversation_history.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    print(f"[{self.name}] Calling tool: {block.name}", flush=True)
                    if block.name.startswith("github_"):
                        result = handle_github_tool_call(block.name, block.input)
                    else:
                        result = handle_port_tool_call(block.name, block.input, self.port_client)
                    print(f"[{self.name}] Tool result: {result[:500]}", flush=True)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
                self.conversation_history.append({"role": "user", "content": tool_results})
                continue

            print(f"[{self.name}] Unexpected stop reason: {response.stop_reason}")
            break

        return final_response or "Agent did not produce a final response."
