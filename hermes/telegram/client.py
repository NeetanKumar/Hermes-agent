"""Thin wrapper around the Telegram Bot API."""

import httpx

API_BASE = "https://api.telegram.org"


class TelegramClient:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"{API_BASE}/bot{token}"

    def get_updates(self, offset: int | None, timeout: int = 30) -> list[dict]:
        """Long-poll for new updates. Blocks up to `timeout` seconds server-side."""
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        # A little slack over the server-side long-poll timeout to avoid
        # racing a slow-but-legitimate response.
        response = httpx.get(f"{self.base_url}/getUpdates", params=params, timeout=timeout + 10)
        response.raise_for_status()
        return response.json().get("result", [])

    def send_message(self, chat_id: int, text: str) -> None:
        # Telegram caps messages at 4096 characters.
        text = text[:4096] if text else "(no response)"
        response = httpx.post(
            f"{self.base_url}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=30.0,
        )
        response.raise_for_status()
