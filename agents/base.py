"""Base agent implementation using Claude Agent SDK."""

import json
import os
from typing import Optional
from anthropic import Anthropic
from tools.port_api import PortAPIClient, create_port_tools, handle_port_tool_call
from tools.port_mcp import PortMCPClient, create_mcp_tool, handle_mcp_tool_call


class BaseAgent:
    """Base class for all agentic SDLC agents."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        api_key: str = None,
        port_api_token: str = None,
        port_base_url: str = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.port_client = PortAPIClient(base_url=port_base_url, api_token=port_api_token)
        # MCP Client uses client credentials from env (PORT_CLIENT_ID, PORT_CLIENT_SECRET)
        self.mcp_client = PortMCPClient()
        self.tools = create_port_tools(self.port_client)
        self.tools.append(create_mcp_tool(self.mcp_client))
        self.conversation_history = []

    def _add_message(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.conversation_history.append({"role": role, "content": content})

    def run(self, user_input: str, max_iterations: int = 10) -> str:
        """
        Run the agent loop with the given input.

        The agent will:
        1. Send the user input + system prompt to Claude
        2. Process Claude's response
        3. If Claude calls a tool, execute it and feed back the result
        4. Repeat until Claude gives a final response or max iterations reached
        """
        self._add_message("user", user_input)
        final_response = None

        for iteration in range(max_iterations):
            print(f"\n[{self.name}] Iteration {iteration + 1}/{max_iterations}")

            # Call Claude with the accumulated conversation history
            response = self.client.messages.create(
                model="claude-opus-5-5",
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools,
                messages=self.conversation_history,
            )

            # Process the response
            stop_reason = response.stop_reason

            if stop_reason == "end_turn":
                # Claude finished without calling a tool - extract the final response
                for block in response.content:
                    if hasattr(block, "text"):
                        final_response = block.text
                        self._add_message("assistant", final_response)
                print(f"[{self.name}] Task completed.")
                break

            elif stop_reason == "tool_use":
                # Claude called one or more tools - process them
                assistant_message = {"role": "assistant", "content": response.content}
                self._add_message("assistant", json.dumps([b.model_dump() if hasattr(b, "model_dump") else str(b) for b in response.content]))

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        print(f"[{self.name}] Calling tool: {tool_name} with input: {json.dumps(tool_input)}")

                        # Execute the tool
                        if tool_name == "port_catalog_query":
                            result = handle_mcp_tool_call(self.mcp_client, tool_name, tool_input)
                        else:
                            result = handle_port_tool_call(tool_name, tool_input, self.port_client)
                        print(f"[{self.name}] Tool result: {result}")

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                # Add tool results to conversation
                self._add_message("user", json.dumps(tool_results))

            else:
                print(f"[{self.name}] Unexpected stop reason: {stop_reason}")
                break

        if final_response is None:
            final_response = "Agent did not produce a final response."

        return final_response

    def get_conversation_history(self) -> list:
        """Return the full conversation history."""
        return self.conversation_history

    def reset(self):
        """Reset the conversation history for a new run."""
        self.conversation_history = []
