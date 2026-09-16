"""WhatsApp Cloud API webhook server.

Run this behind a tunnel (e.g. `ngrok http 8000`) and point a WhatsApp
Cloud API webhook at `<public-url>/webhook`. Each WhatsApp sender gets
their own Hermes conversation, reusing the same Agent/tool-use loop as
the CLI.
"""

import os
import sys
import threading

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from ..agent import Agent
from .client import WhatsAppClient

app = Flask(__name__)

_agents: dict[str, Agent] = {}
_agents_lock = threading.Lock()
_seen_message_ids: set[str] = set()

VERIFY_TOKEN = None
WA_CLIENT: WhatsAppClient | None = None
ALLOWED_NUMBERS: set[str] | None = None
ANTHROPIC_API_KEY = None


def _get_agent(wa_id: str) -> Agent:
    with _agents_lock:
        agent = _agents.get(wa_id)
        if agent is None:
            agent = Agent(api_key=ANTHROPIC_API_KEY)
            _agents[wa_id] = agent
        return agent


def _handle_message(wa_id: str, text: str) -> None:
    try:
        agent = _get_agent(wa_id)
        reply = agent.send(text)
    except Exception as exc:  # noqa: BLE001 - report the failure back to the sender
        reply = f"Error: {exc}"
    try:
        WA_CLIENT.send_text(wa_id, reply)
    except Exception as exc:  # noqa: BLE001 - nothing else we can do but log locally
        print(f"Failed to send WhatsApp reply to {wa_id}: {exc}", file=sys.stderr)


@app.get("/webhook")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge or "", 200
    return "Forbidden", 403


@app.post("/webhook")
def receive_webhook():
    payload = request.get_json(silent=True) or {}
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                message_id = message.get("id")
                if message_id in _seen_message_ids:
                    continue
                _seen_message_ids.add(message_id)

                wa_id = message.get("from")
                text = message.get("text", {}).get("body", "")

                if ALLOWED_NUMBERS and wa_id not in ALLOWED_NUMBERS:
                    print(f"Ignoring message from non-allowed number: {wa_id}", file=sys.stderr)
                    continue

                threading.Thread(target=_handle_message, args=(wa_id, text), daemon=True).start()

    # Ack immediately; replies are sent separately via the Graph API.
    return jsonify({"status": "ok"})


def main() -> None:
    global VERIFY_TOKEN, WA_CLIENT, ALLOWED_NUMBERS, ANTHROPIC_API_KEY

    load_dotenv()
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")
    allowed = os.environ.get("WHATSAPP_ALLOWED_NUMBERS", "").strip()
    ALLOWED_NUMBERS = {n.strip() for n in allowed.split(",") if n.strip()} or None
    port = int(os.environ.get("PORT", "8000"))

    missing = [
        name for name, val in [
            ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
            ("WHATSAPP_TOKEN", token),
            ("WHATSAPP_PHONE_NUMBER_ID", phone_number_id),
            ("WHATSAPP_VERIFY_TOKEN", VERIFY_TOKEN),
        ] if not val
    ]
    if missing:
        print(f"Missing required env vars: {', '.join(missing)}. See .env.example.", file=sys.stderr)
        sys.exit(1)

    WA_CLIENT = WhatsAppClient(token=token, phone_number_id=phone_number_id)

    if sys.platform != "darwin":
        print("Warning: Hermes' app automation only works on macOS.", file=sys.stderr)

    print(f"Hermes WhatsApp bridge listening on :{port} (point ngrok/webhook at /webhook)")
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
