"""Calendar.app automation tools."""

from datetime import datetime, timedelta

from ..applescript import applescript_date_block, escape_applescript_string, run_applescript

FIELD_SEP = "\x1f"
RECORD_SEP = "\x1e"

# Subscribed/system calendars (holidays, birthdays, Siri suggestions) are
# notoriously slow to query via AppleScript's `whose` filter due to heavy
# recurrence expansion. Skip them by default; a user can still ask for one
# explicitly via calendar_name.
SLOW_CALENDAR_PATTERNS = ("holiday", "birthday", "siri suggestions")


def _list_calendar_names() -> list[str]:
    output = run_applescript('tell application "Calendar" to name of calendars')
    if not output:
        return []
    return [name.strip() for name in output.split(",")]


def list_events(days_ahead: int = 1, calendar_name: str | None = None) -> list[dict]:
    """List events starting from now through `days_ahead` days out."""
    days_ahead = max(1, min(int(days_ahead), 90))
    start_block = applescript_date_block("startDate", datetime.now())
    end_block = applescript_date_block("endDate", datetime.now() + timedelta(days=days_ahead))

    if calendar_name:
        cal_esc = escape_applescript_string(calendar_name)
        calendars_expr = f'{{calendar "{cal_esc}"}}'
    else:
        names = [
            n for n in _list_calendar_names()
            if not any(p in n.lower() for p in SLOW_CALENDAR_PATTERNS)
        ]
        if not names:
            return []
        calendars_expr = "{" + ", ".join(f'calendar "{escape_applescript_string(n)}"' for n in names) + "}"

    # Subscribed calendars with heavy recurrence (Holidays, Birthdays, Siri
    # Suggestions) make Calendar.app's `whose` queries pathologically slow —
    # sometimes minutes per calendar. `with timeout ... end timeout` bounds
    # each calendar's query so one slow calendar can't hang the whole call;
    # a calendar that times out is just skipped.
    script = f'''
    {start_block}
    {end_block}
    set out to ""
    tell application "Calendar"
        repeat with cal in {calendars_expr}
            try
                with timeout of 8 seconds
                    set theEvents to (every event of cal whose start date is greater than or equal to startDate and start date is less than or equal to endDate)
                    repeat with evt in theEvents
                        set out to out & (summary of evt) & "{FIELD_SEP}" & ((start date of evt) as string) & "{FIELD_SEP}" & ((end date of evt) as string) & "{FIELD_SEP}" & (name of cal) & "{RECORD_SEP}"
                    end repeat
                end timeout
            end try
        end repeat
    end tell
    return out
    '''
    output = run_applescript(script)
    if not output:
        return []
    events = []
    for record in output.split(RECORD_SEP):
        if not record:
            continue
        summary, start, end, cal_name = record.split(FIELD_SEP)
        events.append({"summary": summary, "start": start, "end": end, "calendar": cal_name})
    return events


def create_event(calendar_name: str, summary: str, start: str, end: str,
                  location: str | None = None) -> dict:
    """Create a calendar event. `start`/`end` are ISO 8601 strings, e.g. 2026-09-20T15:00:00."""
    cal_esc = escape_applescript_string(calendar_name)
    summary_esc = escape_applescript_string(summary)
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    start_block = applescript_date_block("evtStart", start_dt)
    end_block = applescript_date_block("evtEnd", end_dt)

    location_prop = ""
    if location:
        location_esc = escape_applescript_string(location)
        location_prop = f', location:"{location_esc}"'

    script = f'''
    {start_block}
    {end_block}
    tell application "Calendar"
        tell calendar "{cal_esc}"
            make new event with properties {{summary:"{summary_esc}", start date:evtStart, end date:evtEnd{location_prop}}}
        end tell
    end tell
    '''
    run_applescript(script)
    return {"status": "created", "summary": summary, "start": start, "end": end, "calendar": calendar_name}


SCHEMAS = [
    {
        "name": "calendar_list_events",
        "description": "List Calendar.app events from now through N days ahead, across one or all calendars.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {"type": "integer", "description": "How many days ahead to look (default 1 = today)."},
                "calendar_name": {"type": "string", "description": "Restrict to a specific calendar name. Omit to search all calendars."},
            },
        },
    },
    {
        "name": "calendar_create_event",
        "description": "Create a new event in a specific Calendar.app calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "calendar_name": {"type": "string", "description": "Name of the calendar to add the event to."},
                "summary": {"type": "string", "description": "Event title."},
                "start": {"type": "string", "description": "Start time, ISO 8601, e.g. 2026-09-20T15:00:00."},
                "end": {"type": "string", "description": "End time, ISO 8601, e.g. 2026-09-20T16:00:00."},
                "location": {"type": "string", "description": "Optional event location."},
            },
            "required": ["calendar_name", "summary", "start", "end"],
        },
    },
]

DISPATCH = {
    "calendar_list_events": list_events,
    "calendar_create_event": create_event,
}
