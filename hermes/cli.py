"""REPL entrypoint for Hermes."""

import os
import sys

from dotenv import load_dotenv

from .agent import Agent


def main() -> None:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key, "
            "or export it in your shell.",
            file=sys.stderr,
        )
        sys.exit(1)

    if sys.platform != "darwin":
        print("Warning: Hermes' app automation only works on macOS.", file=sys.stderr)

    agent = Agent(api_key=api_key)
    print("Hermes is ready. Ask about your Mail, Calendar, or Reminders (Ctrl+C to quit).")

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        try:
            reply = agent.send(user_input)
        except Exception as exc:  # noqa: BLE001 - keep the REPL alive on errors
            print(f"Error: {exc}", file=sys.stderr)
            continue
        print(reply)


if __name__ == "__main__":
    main()
