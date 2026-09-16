"""Thin wrapper around the WhatsApp Cloud API for sending messages."""

import httpx

GRAPH_API_VERSION = "v20.0"


class WhatsAppClient:
    def __init__(self, token: str, phone_number_id: str):
        self.token = token
        self.phone_number_id = phone_number_id
        self.base_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"

    def send_text(self, to: str, body: str) -> None:
        """Send a plain-text WhatsApp message to `to` (E.164 number, no leading +)."""
        # WhatsApp messages are capped at 4096 characters.
        body = body[:4096] if body else "(no response)"
        response = httpx.post(
            self.base_url,
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": body},
            },
            timeout=30.0,
        )
        response.raise_for_status()
