"""Reminders.app automation tools."""

from datetime import datetime

from ..applescript import applescript_date_block, escape_applescript_string, run_applescript

FIELD_SEP = "\x1f"
RECORD_SEP = "\x1e"


def list_reminders(list_name: str | None = None, include_completed: bool = False) -> list[dict]:
    """List reminders, optionally scoped to a specific list."""
    filter_clause = "" if include_completed else " whose completed is false"

    if list_name:
        list_esc = escape_applescript_string(list_name)
        lists_expr = f'{{list "{list_esc}"}}'
    else:
        lists_expr = "lists"

    script = f'''
    set out to ""
    tell application "Reminders"
        repeat with lst in {lists_expr}
            set theReminders to (reminders of lst{filter_clause})
            repeat with rem in theReminders
                set dueStr to "none"
                if due date of rem is not missing value then set dueStr to ((due date of rem) as string)
                set out to out & (id of rem as string) & "{FIELD_SEP}" & (name of rem) & "{FIELD_SEP}" & dueStr & "{FIELD_SEP}" & (completed of rem as string) & "{FIELD_SEP}" & (name of lst) & "{RECORD_SEP}"
            end repeat
        end repeat
    end tell
    return out
    '''
    output = run_applescript(script)
    if not output:
        return []
    reminders = []
    for record in output.split(RECORD_SEP):
        if not record:
            continue
        rem_id, name, due, completed, list_nm = record.split(FIELD_SEP)
        reminders.append({
            "id": rem_id,
            "name": name,
            "due": None if due == "none" else due,
            "completed": completed == "true",
            "list": list_nm,
        })
    return reminders


def create_reminder(name: str, list_name: str = "Reminders", due: str | None = None,
                     notes: str | None = None) -> dict:
    """Create a reminder. `due`, if given, is an ISO 8601 datetime string."""
    name_esc = escape_applescript_string(name)
    list_esc = escape_applescript_string(list_name)

    due_block = ""
    due_prop = ""
    if due:
        due_dt = datetime.fromisoformat(due)
        due_block = applescript_date_block("remDue", due_dt)
        due_prop = ", due date:remDue"

    notes_prop = ""
    if notes:
        notes_esc = escape_applescript_string(notes)
        notes_prop = f', body:"{notes_esc}"'

    script = f'''
    {due_block}
    tell application "Reminders"
        tell list "{list_esc}"
            make new reminder with properties {{name:"{name_esc}"{due_prop}{notes_prop}}}
        end tell
    end tell
    '''
    run_applescript(script)
    return {"status": "created", "name": name, "list": list_name, "due": due}


def complete_reminder(reminder_id: str) -> dict:
    """Mark a reminder as completed by its id (from list_reminders)."""
    script = f'''
    tell application "Reminders"
        set theReminders to (reminders whose id is {int(reminder_id)})
        if (count of theReminders) is 0 then return "NOT_FOUND"
        set completed of item 1 of theReminders to true
        return "OK"
    end tell
    '''
    output = run_applescript(script)
    if output == "NOT_FOUND":
        return {"error": f"No reminder with id {reminder_id}"}
    return {"status": "completed", "id": reminder_id}


SCHEMAS = [
    {
        "name": "reminders_list",
        "description": "List reminders from Reminders.app, optionally scoped to one list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "list_name": {"type": "string", "description": "Restrict to a specific list name. Omit to search all lists."},
                "include_completed": {"type": "boolean", "description": "Include already-completed reminders."},
            },
        },
    },
    {
        "name": "reminders_create",
        "description": "Create a new reminder in Reminders.app.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Reminder title/text."},
                "list_name": {"type": "string", "description": "List to add the reminder to (default 'Reminders')."},
                "due": {"type": "string", "description": "Optional due date/time, ISO 8601, e.g. 2026-09-20T15:00:00."},
                "notes": {"type": "string", "description": "Optional notes body."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "reminders_complete",
        "description": "Mark a reminder as completed by its id (from reminders_list).",
        "input_schema": {
            "type": "object",
            "properties": {
                "reminder_id": {"type": "string", "description": "The reminder id returned by reminders_list."},
            },
            "required": ["reminder_id"],
        },
    },
]

DISPATCH = {
    "reminders_list": list_reminders,
    "reminders_create": create_reminder,
    "reminders_complete": complete_reminder,
}
