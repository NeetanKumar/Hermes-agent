"""Tool schemas and dispatch table for the Hermes agent."""

from . import calendar, mail, reminders

TOOL_SCHEMAS = [
    *mail.SCHEMAS,
    *calendar.SCHEMAS,
    *reminders.SCHEMAS,
]

DISPATCH = {
    **mail.DISPATCH,
    **calendar.DISPATCH,
    **reminders.DISPATCH,
}
