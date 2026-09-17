"""Mail.app automation tools."""

from datetime import datetime, timedelta

from ..applescript import applescript_date_block, escape_applescript_string, run_applescript

FIELD_SEP = "\x1f"
RECORD_SEP = "\x1e"

# IMAP accounts (Gmail in particular) nest their special mailboxes under the
# account rather than exposing them as top-level mailboxes, and often use
# provider-specific names ("Sent Mail" rather than "Sent"). A bare
# `mailbox "Sent"` reference fails for these with a cryptic AppleScript
# error (-1728), so common names are resolved against the account's real
# mailbox list instead of guessed.
MAILBOX_ALIASES = {
    "sent": ["sent mail", "sent messages", "sent items", "sent"],
    "drafts": ["drafts"],
    "trash": ["trash", "deleted messages", "bin"],
    "junk": ["junk", "spam", "junk e-mail"],
}


def _list_account_mailboxes() -> list[tuple[str, str]]:
    """Return (account_name, mailbox_name) pairs for every account's mailboxes."""
    script = '''
    set out to ""
    tell application "Mail"
        repeat with acc in accounts
            repeat with mb in mailboxes of acc
                set out to out & (name of acc) & "\x1f" & (name of mb) & "\x1e"
            end repeat
        end repeat
    end tell
    return out
    '''
    output = run_applescript(script)
    if not output:
        return []
    pairs = []
    for record in output.split(RECORD_SEP):
        if not record:
            continue
        account_name, mailbox_name = record.split(FIELD_SEP)
        pairs.append((account_name, mailbox_name))
    return pairs


def _mailbox_ref(mailbox: str) -> str:
    normalized = mailbox.strip().lower()
    if normalized == "inbox":
        return "inbox"

    pairs = _list_account_mailboxes()
    candidates = [normalized] + MAILBOX_ALIASES.get(normalized, [])
    for candidate in candidates:
        for account_name, mailbox_name in pairs:
            if mailbox_name.lower() == candidate:
                # `mailbox "X" of account "Y"` fails with -1728 for IMAP-nested
                # mailboxes (observed on Gmail); the `whose` filter form works.
                return (
                    f'first mailbox of account "{escape_applescript_string(account_name)}" '
                    f'whose name is "{escape_applescript_string(mailbox_name)}"'
                )

    available = ", ".join(f"{acc}/{mb}" for acc, mb in pairs) or "(none found)"
    raise ValueError(f'No mailbox matching "{mailbox}". Available mailboxes: {available}')


def list_messages(mailbox: str = "INBOX", limit: int = 10, unread_only: bool = False,
                   sender_contains: str | None = None, subject_contains: str | None = None,
                   since_days: int | None = None) -> list[dict]:
    """List recent messages in a mailbox, newest first."""
    limit = max(1, min(int(limit), 200))
    mailbox_ref = _mailbox_ref(mailbox)

    since_block = ""
    conditions = []
    if unread_only:
        conditions.append("read status is false")
    if sender_contains:
        sender_esc = escape_applescript_string(sender_contains)
        conditions.append(f'sender contains "{sender_esc}"')
    if subject_contains:
        subject_esc = escape_applescript_string(subject_contains)
        conditions.append(f'subject contains "{subject_esc}"')
    if since_days is not None:
        cutoff = datetime.now() - timedelta(days=max(1, int(since_days)))
        since_block = applescript_date_block("sinceDate", cutoff)
        conditions.append("date received > sinceDate")
    whose_clause = f" whose {' and '.join(conditions)}" if conditions else ""

    script = f'''
    {since_block}
    set out to ""
    tell application "Mail"
        set theMailbox to {mailbox_ref}
        set theMessages to (messages of theMailbox{whose_clause})
        set theCount to count of theMessages
        set upperBound to {limit}
        if theCount < upperBound then set upperBound to theCount
        repeat with i from 1 to upperBound
            set msg to item i of theMessages
            set out to out & (id of msg as string) & "{FIELD_SEP}" & (subject of msg) & "{FIELD_SEP}" & (sender of msg) & "{FIELD_SEP}" & ((date received of msg) as string) & "{FIELD_SEP}" & (read status of msg as string) & "{RECORD_SEP}"
        end repeat
    end tell
    return out
    '''
    output = run_applescript(script)
    if not output:
        return []
    messages = []
    for record in output.split(RECORD_SEP):
        if not record:
            continue
        msg_id, subject, sender, date_received, read_status = record.split(FIELD_SEP)
        messages.append({
            "id": msg_id,
            "subject": subject,
            "sender": sender,
            "date_received": date_received,
            "unread": read_status == "false",
        })
    return messages


def read_message(message_id: str, mailbox: str = "INBOX") -> dict:
    """Read the full content of a message by its id (as returned by list_messages)."""
    mailbox_ref = _mailbox_ref(mailbox)
    script = f'''
    tell application "Mail"
        set theMailbox to {mailbox_ref}
        set theMessages to (messages of theMailbox whose id is {int(message_id)})
        if (count of theMessages) is 0 then return "NOT_FOUND"
        set msg to item 1 of theMessages
        return (subject of msg) & "{FIELD_SEP}" & (sender of msg) & "{FIELD_SEP}" & (content of msg)
    end tell
    '''
    output = run_applescript(script)
    if output == "NOT_FOUND":
        return {"error": f"No message with id {message_id} in mailbox {mailbox}"}
    subject, sender, content = output.split(FIELD_SEP, 2)
    return {"subject": subject, "sender": sender, "content": content}


def send_message(to: str, subject: str, body: str) -> dict:
    """Compose and send an email."""
    to_esc = escape_applescript_string(to)
    subject_esc = escape_applescript_string(subject)
    body_esc = escape_applescript_string(body)
    script = f'''
    tell application "Mail"
        set newMsg to make new outgoing message with properties {{subject:"{subject_esc}", content:"{body_esc}", visible:false}}
        tell newMsg
            make new to recipient at end of to recipients with properties {{address:"{to_esc}"}}
            send
        end tell
    end tell
    '''
    run_applescript(script)
    return {"status": "sent", "to": to, "subject": subject}


def list_mailboxes() -> list[dict]:
    """List every mailbox name available, grouped by account."""
    return [{"account": acc, "mailbox": mb} for acc, mb in _list_account_mailboxes()]


SCHEMAS = [
    {
        "name": "mail_list_mailboxes",
        "description": "List all available mailbox names per account (e.g. to find the real name of Sent/Drafts/Trash on an account like Gmail, which nests and renames them).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "mail_list_messages",
        "description": "List recent messages in a Mail.app mailbox, newest first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mailbox": {"type": "string", "description": "Mailbox name. Defaults to INBOX, which only holds messages *received* — it never contains your own sent replies. For a full two-sided conversation/thread with someone, use 'All Mail' instead (present on Gmail accounts; holds both sent and received copies of every message). Call mail_list_mailboxes if unsure what's available on this account."},
                "limit": {"type": "integer", "description": "Max number of messages to return (1-200). Use a high limit combined with since_days for date-range questions, since results are not otherwise guaranteed to cover the full range."},
                "unread_only": {"type": "boolean", "description": "Only return unread messages."},
                "sender_contains": {"type": "string", "description": "Filter messages whose sender contains this text. Note: this only matches messages *from* that person — your own sent replies to them have you as the sender, so this filter alone will miss half a conversation. To get the full thread, also run a second search with subject_contains set to the thread's subject (stripped of 'Re:'/'Fwd:' prefixes) against 'All Mail', which will surface your side too."},
                "subject_contains": {"type": "string", "description": "Filter messages whose subject contains this text. Useful for pulling a full thread (both sent and received) by subject once you know it, since sender_contains alone can't do that."},
                "since_days": {"type": "integer", "description": "Only return messages received within the last N days, e.g. 30 for 'last month'. Always set this for time-bounded questions instead of relying on limit alone."},
            },
        },
    },
    {
        "name": "mail_read_message",
        "description": "Read the full content of a specific email by its id (from mail_list_messages).",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "The message id returned by mail_list_messages."},
                "mailbox": {"type": "string", "description": "Mailbox the message lives in. Defaults to INBOX."},
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "mail_send_message",
        "description": "Compose and send a new email via Mail.app.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address."},
                "subject": {"type": "string", "description": "Email subject."},
                "body": {"type": "string", "description": "Email body text."},
            },
            "required": ["to", "subject", "body"],
        },
    },
]

DISPATCH = {
    "mail_list_mailboxes": list_mailboxes,
    "mail_list_messages": list_messages,
    "mail_read_message": read_message,
    "mail_send_message": send_message,
}
