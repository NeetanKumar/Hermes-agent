# Hermes

A local chat agent that automates macOS Mail, Calendar, and Reminders. Talk to it
in plain English; it decides which app actions to take and runs them for you via
AppleScript.

Runs entirely on your own Mac — anyone can install it and use it with their own
Anthropic API key. It does not talk to any server other than the Anthropic API.

## Requirements

- macOS
- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

## Install

```bash
git clone https://github.com/NeetanKumar/Hermes-agent.git
cd Hermes-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configure

```bash
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
hermes
```

Then just ask, e.g.:

- "What's on my calendar today?"
- "Create a reminder to call the bank tomorrow at 3pm."
- "Do I have any unread mail from Alice?"

On first use, macOS will prompt you to grant Terminal (or your Python interpreter)
permission to control Mail, Calendar, and Reminders under
**System Settings > Privacy & Security > Automation**. Approve these prompts for
Hermes to work.

## How it works

Hermes uses Claude's tool-use API: your message and a set of tool definitions
(one per app action) are sent to Claude, which decides which tool(s) to call.
Hermes runs those locally via AppleScript (`osascript`) and feeds the results
back to Claude until it has a final reply. See [PLAN.md](PLAN.md) for the design.
