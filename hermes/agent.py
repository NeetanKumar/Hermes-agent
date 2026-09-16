"""Claude tool-use loop that drives the desktop automation tools."""

import json

from anthropic import Anthropic

from .tools import DISPATCH, TOOL_SCHEMAS

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = (
    "You are Hermes, a local desktop assistant that can read and act on the user's "
    "Mail, Calendar, and Reminders apps via the tools provided. Be concise. "
    "Confirm destructive or sending actions (like sending an email) are what the "
    "user asked for before or after doing them, but don't ask permission for read-only "
    "actions like listing messages or events."
)


class Agent:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.messages: list[dict] = []

    def send(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        while True:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=self.messages,
            )
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                return "".join(block.text for block in response.content if block.type == "text")

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result = self._run_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })
            self.messages.append({"role": "user", "content": tool_results})

    def _run_tool(self, name: str, tool_input: dict):
        func = DISPATCH.get(name)
        if func is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            return func(**tool_input)
        except Exception as exc:  # noqa: BLE001 - surfaced to the model as a tool error
            return {"error": str(exc)}
