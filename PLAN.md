# Hermes: Desktop Automation Chat Agent

## Context

The user is setting up "Hermes," a personal project (unrelated to the YC startup Kiwi AI — that guess was ruled out). Hermes is a standalone, local, Python-based chat agent that automates native macOS apps on the user's desktop, starting with **Mail, Calendar, and Reminders**. The user talks to it conversationally; it decides which app actions to take and executes them, using whichever automation mechanism fits each app (AppleScript first, since Mail/Calendar/Reminders are all natively AppleScript-scriptable; the architecture stays open to Accessibility API or vision-based control for apps that need it later).

The repo (`/Users/neetan.kumar/Desktop/Hermes-agent`) currently contains only a `README.md` and is pushed to `https://github.com/NeetanKumar/Hermes-agent`. This plan sets up the initial working skeleton.

## Approach

**LLM/chat loop**: Use the Anthropic Python SDK (`anthropic` package) directly with a tool-use loop — this is a lightweight, dependency-light choice appropriate for a personal CLI agent (no need for the full Claude Agent SDK's harness features here). Claude receives the user's message plus a set of tool definitions (one per app action), decides which tool(s) to call, Hermes executes them locally via AppleScript, and results are fed back to Claude until it produces a final natural-language reply.

**App automation**: Each app gets its own module wrapping `osascript` (AppleScript) calls for the actions the user is most likely to want:
- Mail: search/list recent messages, read a message, send a message
- Calendar: list events (today/date range), create an event
- Reminders: list reminders (by list/due date), create a reminder, mark complete

**Interface**: A simple REPL (`hermes` command / `python -m hermes.cli`) that keeps a running conversation with Claude and prints tool actions as they happen for transparency.

## Structure

```
Hermes-agent/
  hermes/
    __init__.py
    cli.py            # REPL entrypoint, conversation loop
    agent.py          # Claude API tool-use loop (send message, dispatch tool calls, loop to final reply)
    applescript.py    # run_applescript() helper: subprocess wrapper around `osascript`, error handling
    tools/
      __init__.py     # TOOL_SCHEMAS list + dispatch table combining all app tools
      mail.py         # list_messages, read_message, send_message
      calendar.py     # list_events, create_event
      reminders.py    # list_reminders, create_reminder, complete_reminder
  pyproject.toml       # anthropic dependency, `hermes` console-script entry point
  .env.example         # ANTHROPIC_API_KEY=
  .gitignore           # .env, __pycache__/, .venv/, *.egg-info/
  README.md            # update: what Hermes is, setup (venv, pip install -e ., API key), usage, macOS Automation permission note
```

## Key implementation details

- `applescript.py`: a single `run_applescript(script: str) -> str` that shells out to `osascript -e`, raises a clear error on non-zero exit (surfacing AppleScript's own error message), and is the only place subprocess calls happen — keeps injection risk contained since script strings are built from controlled templates, not raw string-concatenated user input.
- `tools/*.py`: each function builds a parameterized AppleScript string (escaping any interpolated text) and returns a small JSON-serializable result (e.g. list of dicts) that gets fed back to Claude as the tool result.
- `agent.py`: holds the Anthropic client, the tool schema list (JSON schema per tool, name/description/input_schema), and the loop: send messages → if `stop_reason == "tool_use"`, run each tool via a name→function dispatch dict, append `tool_result` blocks, call again → else return the text reply.
- `cli.py`: reads `ANTHROPIC_API_KEY` from env (via `python-dotenv` loading `.env`), starts a loop reading user input, calls `agent.send(conversation, user_input)`, prints the reply.
- First run will trigger macOS "Automation" permission prompts (Terminal/Python wanting to control Mail/Calendar/Reminders) — note this in the README so the user isn't surprised.

## Verification

1. `cd Hermes-agent && python3 -m venv .venv && source .venv/bin/activate && pip install -e .`
2. Copy `.env.example` to `.env`, add a real `ANTHROPIC_API_KEY`.
3. Run `hermes`, try: "What's on my calendar today?" — grant the macOS Automation permission prompt when it appears — confirm it lists real events.
4. Try: "Create a reminder to call the bank tomorrow at 3pm" — confirm it appears in Reminders.app.
5. Try: "Do I have any unread mail from Alice?" — confirm it searches Mail correctly.
