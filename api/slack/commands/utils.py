from datetime import datetime, timedelta
from typing import Dict, Optional

from django.utils import timezone


def bool_str(bl: bool) -> str:
    """Convert a bool to a Yes/No string."""
    return "Yes" if bl else "No"


def format_stats_section(name: str, section: Dict) -> str:
    """Format a given section of stats to a readable string.

    Example:
    *Section name*:
    - Key 1: Value 1
    - Key 2: Value 2
    """
    section_items = "\n".join([f"- {key}: {value}" for key, value in section.items()])

    return f"*{name}*:\n{section_items}"


def format_time(time: Optional[datetime]) -> Optional[str]:
    """Format the given time in absolute and relative strings."""
    if time is None:
        return None

    now = timezone.now()
    absolute = time.date().isoformat()

    relative_delta = now - time
    relative = relative_duration(relative_delta)

    if now >= time:
        return f"{absolute} ({relative} ago)"
    else:
        return f"{absolute} (in {relative})"


def relative_duration(delta: timedelta) -> str:
    """Format the delta into a relative time string."""
    seconds = abs(delta.total_seconds())
    minutes = seconds / 60
    hours = minutes / 60
    days = hours / 24
    weeks = days / 7
    months = days / 30
    years = days / 365

    # Determine major time unit
    if years >= 1:
        value, unit = years, "year"
    elif months >= 1:
        value, unit = months, "month"
    elif weeks >= 1:
        value, unit = weeks, "week"
    elif days >= 1:
        value, unit = days, "day"
    elif hours >= 1:
        value, unit = hours, "hour"
    elif minutes >= 1:
        value, unit = minutes, "min"
    elif seconds > 5:
        value, unit = seconds, "sec"
    else:
        duration_ms = seconds / 1000
        value, unit = duration_ms, "ms"

    if unit == "ms":
        duration_str = f"{value:0.0f} ms"
    else:
        # Add plural s if necessary
        if value != 1:
            unit += "s"

        duration_str = f"{value:.1f} {unit}"

    return duration_str
