"""Telegram long-polling bridge.

No public webhook or tunnel needed: this process asks Telegram "any new
messages?" (long-poll, up to 30s per request) and reacts to what comes
back. Each Telegram chat gets its own Hermes conversation, reusing the
same Agent/tool-use loop as the CLI.
"""

import os
import sys
import threading

import httpx
from dotenv import load_dotenv

from ..agent import Agent
from .client import TelegramClient

_agents: dict[int, Agent] = {}
_agents_lock = threading.Lock()


def _get_agent(chat_id: int, api_key: str) -> Agent:
    with _agents_lock:
        agent = _agents.get(chat_id)
        if agent is None:
            agent = Agent(api_key=api_key)
            _agents[chat_id] = agent
        return agent


def _handle_message(client: TelegramClient, api_key: str, chat_id: int, text: str) -> None:
    try:
        agent = _get_agent(chat_id, api_key)
        reply = agent.send(text)
    except Exception as exc:  # noqa: BLE001 - report the failure back to the sender
        reply = f"Error: {exc}"
    try:
        client.send_message(chat_id, reply)
    except Exception as exc:  # noqa: BLE001 - nothing else we can do but log locally
        print(f"Failed to send Telegram reply to {chat_id}: {exc}", file=sys.stderr)


def main() -> None:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    allowed = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
    allowed_ids = {int(x) for x in allowed.split(",") if x.strip()} or None

    missing = [
        name for name, val in [("ANTHROPIC_API_KEY", api_key), ("TELEGRAM_BOT_TOKEN", token)]
        if not val
    ]
    if missing:
        print(f"Missing required env vars: {', '.join(missing)}. See .env.example.", file=sys.stderr)
        sys.exit(1)

    if sys.platform != "darwin":
        print("Warning: Hermes' app automation only works on macOS.", file=sys.stderr)

    client = TelegramClient(token=token)
    offset = None
    print("Hermes Telegram bridge running. Message your bot on Telegram (Ctrl+C to quit).")

    try:
        while True:
            try:
                updates = client.get_updates(offset=offset, timeout=30)
            except Exception as exc:  # noqa: BLE001 - transient network errors shouldn't kill the loop
                print(f"Poll error: {exc}", file=sys.stderr)
                continue

            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message") or update.get("edited_message")
                if not message or "text" not in message:
                    continue
                chat_id = message["chat"]["id"]
                if allowed_ids and chat_id not in allowed_ids:
                    print(f"Ignoring message from non-allowed chat_id: {chat_id}", file=sys.stderr)
                    continue
                threading.Thread(
                    target=_handle_message,
                    args=(client, api_key, chat_id, message["text"]),
                    daemon=True,
                ).start()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
