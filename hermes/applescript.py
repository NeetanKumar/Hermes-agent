"""Helper for running AppleScript via osascript."""

import subprocess
from datetime import datetime


class AppleScriptError(RuntimeError):
    pass


def run_applescript(script: str) -> str:
    """Run an AppleScript string via osascript and return stdout, stripped.

    Raises AppleScriptError with osascript's own error message on failure.
    """
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AppleScriptError(result.stderr.strip() or "osascript failed")
    return result.stdout.strip()


def escape_applescript_string(value: str) -> str:
    """Escape a string for safe interpolation into an AppleScript string literal."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def applescript_date_block(var_name: str, dt: datetime) -> str:
    """Build AppleScript statements that set `var_name` to a specific date.

    Setting numeric fields on a fresh `current date` avoids locale-dependent
    date-string parsing, which is unreliable across AppleScript locales.
    """
    return (
        f"set {var_name} to current date\n"
        f"set year of {var_name} to {dt.year}\n"
        f"set month of {var_name} to {dt.month}\n"
        f"set day of {var_name} to {dt.day}\n"
        f"set hours of {var_name} to {dt.hour}\n"
        f"set minutes of {var_name} to {dt.minute}\n"
        f"set seconds of {var_name} to {dt.second}\n"
    )
