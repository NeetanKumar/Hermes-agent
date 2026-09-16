"""Calendar.app automation tools."""

from datetime import datetime, timedelta

from ..applescript import applescript_date_block, escape_applescript_string, run_applescript

FIELD_SEP = "\x1f"
RECORD_SEP = "\x1e"


def list_events(days_ahead: int = 1, calendar_name: str | None = None) -> list[dict]:
    """List events starting from now through `days_ahead` days out."""
    days_ahead = max(1, min(int(days_ahead), 90))
    start_block = applescript_date_block("startDate", datetime.now())
    end_block = applescript_date_block("endDate", datetime.now() + timedelta(days=days_ahead))

    if calendar_name:
        cal_esc = escape_applescript_string(calendar_name)
        calendars_expr = f'{{calendar "{cal_esc}"}}'
    else:
        calendars_expr = "calendars"

    script = f'''
    {start_block}
    {end_block}
    set out to ""
    tell application "Calendar"
        repeat with cal in {calendars_expr}
            set theEvents to (every event of cal whose start date is greater than or equal to startDate and start date is less than or equal to endDate)
            repeat with evt in theEvents
                set out to out & (summary of evt) & "{FIELD_SEP}" & ((start date of evt) as string) & "{FIELD_SEP}" & ((end date of evt) as string) & "{FIELD_SEP}" & (name of cal) & "{RECORD_SEP}"
            end repeat
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
