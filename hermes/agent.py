"""Claude tool-use loop that drives the desktop automation tools."""

import json
import threading

from anthropic import Anthropic

from .tools import DISPATCH, TOOL_SCHEMAS
from .tools.mail import get_own_identities

MODEL = "claude-sonnet-5"
REQUEST_TIMEOUT = 60.0
HEARTBEAT_INTERVAL = 5.0
MAX_TOKENS = 4096

BASE_SYSTEM_PROMPT = (
    "You are Hermes, a local desktop assistant that can read and act on the user's "
    "Mail, Calendar, and Reminders apps via the tools provided. Be concise. "
    "For time-bounded mail questions (e.g. 'in the last month'), always pass "
    "since_days to mail_list_messages rather than relying on limit alone, and "
    "raise limit generously (e.g. 100+) so results aren't silently truncated. "
    "Classifying emails (e.g. 'is this a rejection?') from subject/sender alone can "
    "be ambiguous — use mail_read_message on borderline cases before counting them, "
    "and state any assumptions you made in the answer. "
    "When asked to review a mail 'chain', 'thread', or 'conversation' with someone, "
    "never rely on a single sender_contains search against INBOX — that only shows "
    "messages received, never the user's own replies, so it's structurally one-sided. "
    "Search 'All Mail' instead (or call mail_list_mailboxes if unsure it exists), and "
    "once you see a subject, do a follow-up subject_contains search on 'All Mail' to "
    "pull in both sides of the thread before summarizing or suggesting a follow-up. "
    "Always check whether the user already replied to the most recent message before "
    "suggesting they follow up — but check each message's is_draft field first: a "
    "draft was never sent, so it doesn't count as a reply and doesn't move the ball "
    "into the other person's court. Point out explicitly if the 'most recent' item in "
    "a thread is actually an unsent draft. "
    "Never end a turn by announcing what you're about to check next ('I'll look into "
    "X') without actually calling the tool in that same turn — either call it now or "
    "give the complete final answer now. "
    "Confirm destructive or sending actions (like sending an email) are what the "
    "user asked for before or after doing them, but don't ask permission for read-only "
    "actions like listing messages or events."
)


def _build_system_prompt() -> str:
    # Without knowing the user's own identity, the agent can misread the
    # user's own sent messages in a thread as belonging to a third party
    # (e.g. describing "Neetan Kumar" as someone other than the user).
    try:
        identities = get_own_identities()
    except Exception:  # noqa: BLE001 - identity lookup is a nice-to-have, not required
        identities = []
    if not identities:
        return BASE_SYSTEM_PROMPT
    who = "; ".join(f'{i["name"]} <{i["email"]}>' for i in identities)
    return (
        BASE_SYSTEM_PROMPT
        + f" The user's own Mail identity is: {who}. Messages sent from this name/"
        "address are messages FROM THE USER, not from a third party — never describe "
        "the user's own sent messages as belonging to someone else in a thread."
    )


class Agent:
    def __init__(self, api_key: str, on_event=None):
        # Explicit timeout: without one, a stalled connection can hang
        # indefinitely with no error and no feedback.
        self.client = Anthropic(api_key=api_key, timeout=REQUEST_TIMEOUT)
        self.messages: list[dict] = []
        self.system_prompt = _build_system_prompt()
        # on_event(kind: str, detail: str) is called for "thinking", "heartbeat",
        # "tool_call", and "tool_result" so a caller (e.g. the CLI) can show liveness.
        self.on_event = on_event or (lambda kind, detail: None)

    def _create_with_heartbeat(self, **kwargs):
        stop = threading.Event()

        def beat():
            elapsed = 0.0
            while not stop.wait(HEARTBEAT_INTERVAL):
                elapsed += HEARTBEAT_INTERVAL
                self.on_event("heartbeat", f"{elapsed:.0f}s")

        thread = threading.Thread(target=beat, daemon=True)
        thread.start()
        try:
            return self.client.messages.create(**kwargs)
        finally:
            stop.set()
            thread.join()

    def send(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        while True:
            self.on_event("thinking", "")
            response = self._create_with_heartbeat(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=self.system_prompt,
                tools=TOOL_SCHEMAS,
                messages=self.messages,
            )
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "max_tokens":
                self.on_event("warning", "response cut off at max_tokens")
                text = "".join(block.text for block in response.content if block.type == "text")
                return text or (
                    "(I ran out of response budget mid-thought and didn't produce an "
                    "answer. Try asking again, maybe more narrowly.)"
                )

            if response.stop_reason != "tool_use":
                return "".join(block.text for block in response.content if block.type == "text")

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                self.on_event("tool_call", f"{block.name}({block.input})")
                result = self._run_tool(block.name, block.input)
                self.on_event("tool_result", f"{block.name} -> {result}")
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
