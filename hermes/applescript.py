"""Helper for running AppleScript via osascript."""

import subprocess
from datetime import datetime


class AppleScriptError(RuntimeError):
    pass


def run_applescript(script: str, timeout: float = 45) -> str:
    """Run an AppleScript string via osascript and return stdout, stripped.

    Raises AppleScriptError with osascript's own error message on failure,
    or on timeout (most likely an unanswered macOS Automation permission
    prompt sitting on screen).
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise AppleScriptError(
            f"Timed out after {timeout}s waiting on osascript. Check your screen for "
            "a macOS permission prompt (System Settings > Privacy & Security > "
            "Automation) and approve it, then try again."
        ) from exc
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
