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

## Use from Telegram

The easiest way to talk to Hermes from your phone: no public webhook, no
tunnel, no business app review — just a bot token.

**1. Create the bot**

Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`,
follow the prompts. It gives you a token like `123456:ABC-DEF...`.

**2. Configure Hermes**

Add to `.env`:

```
TELEGRAM_BOT_TOKEN=<the token from BotFather>
```

**3. Run it**

```bash
hermes-telegram
```

That's it — message your bot on Telegram and it replies. It works by
long-polling Telegram for new messages (no inbound connection needed), so
there's nothing else to configure. Each Telegram chat gets its own Hermes
conversation, backed by the same agent that powers the `hermes` CLI.

By default anyone who finds your bot's username can message it. To restrict
it to yourself, message your bot once, then check
`https://api.telegram.org/bot<token>/getUpdates` for your `chat.id`, and set
`TELEGRAM_ALLOWED_CHAT_IDS=<that id>` in `.env`.

## Use from WhatsApp

Hermes can also run as a WhatsApp bot using the official WhatsApp Cloud API,
so you can message it from your phone instead of a terminal. This requires a
Meta Developer app and a public URL for Meta to call (via a tunnel like
ngrok, since Hermes still runs on your Mac and needs local AppleScript
access).

**1. Create the Meta app and test number**

1. Go to [developers.facebook.com](https://developers.facebook.com/) →
   create an app → add the **WhatsApp** product.
2. Under WhatsApp > API Setup you get a temporary access token and a test
   phone number (free, no business verification needed to start).
3. Under API Setup, add your own phone number as an allowed **recipient**
   (test numbers can only message pre-approved testers) and verify it via
   the code WhatsApp sends you.

**2. Configure Hermes**

Add to `.env`:

```
WHATSAPP_TOKEN=<the access token from API Setup>
WHATSAPP_PHONE_NUMBER_ID=<the phone number ID from API Setup>
WHATSAPP_VERIFY_TOKEN=<any string you make up, e.g. hermes-verify-123>
WHATSAPP_ALLOWED_NUMBERS=<your number in E.164 without +, e.g. 919876543210>
```

**3. Run the bridge and tunnel**

```bash
hermes-whatsapp          # starts the webhook server on :8000
ngrok http 8000          # in a second terminal — gives you a public https URL
```

**4. Point the webhook at ngrok**

In the Meta app dashboard, under WhatsApp > Configuration:

- **Callback URL**: `https://<your-ngrok-domain>/webhook`
- **Verify token**: the same value you set as `WHATSAPP_VERIFY_TOKEN`
- Subscribe to the `messages` webhook field.

Note the free ngrok URL changes every time you restart it — update the
Callback URL in Meta's dashboard each time, or use a paid ngrok static
domain to avoid that.

**5. Message it**

Text your Meta test number from your phone (the number you verified as a
tester). Each WhatsApp sender gets their own Hermes conversation, backed by
the same agent that powers the `hermes` CLI.

The temporary access token from API Setup expires in 24 hours — for
longer-lived use, generate a permanent token via a System User in Meta
Business Settings.

## How it works

Hermes uses Claude's tool-use API: your message and a set of tool definitions
(one per app action) are sent to Claude, which decides which tool(s) to call.
Hermes runs those locally via AppleScript (`osascript`) and feeds the results
back to Claude until it has a final reply. See [PLAN.md](PLAN.md) for the design.

## Note: not the same project as "Hermes Agent" by Nous Research

There's a separate, unrelated open-source project also called "Hermes Agent"
(`github.com/NousResearch/hermes-agent`) — a much larger general-purpose
self-hosted agent platform (persistent memory, 40+ skills, 5 chat platforms,
cloud/Docker execution backends). Pure name collision, not related to this
repo. Its terminal setup, kept here for reference since it's easy to miss in
their README:

```bash
# Install (macOS/Linux/WSL2)
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Reload shell, then run
source ~/.zshrc
hermes
```

Other commands: `hermes model` (choose LLM provider), `hermes tools`
(configure enabled tools), `hermes setup` (full setup wizard), `hermes
gateway` (start the messaging gateway for Telegram/Discord/Slack/WhatsApp/
Signal), `hermes update`, `hermes doctor`.
