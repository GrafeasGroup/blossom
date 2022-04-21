from datetime import datetime, timedelta
from typing import Dict

from django.utils import timezone

from api.serializers import VolunteerSerializer
from api.slack import client
from api.slack.utils import dict_to_table, parse_user
from api.views.misc import Summary
from authentication.models import BlossomUser
from blossom.strings import translation

i18n = translation()


def info_cmd(channel: str, message: str) -> None:
    """Send info about a user to slack."""
    parsed_message = message.split()
    if len(parsed_message) == 1:
        # they just sent an empty info message, create a summary response
        data = Summary().generate_summary()
        client.chat_postMessage(
            channel=channel,
            text=i18n["slack"]["server_summary"].format("\n".join(dict_to_table(data))),
        )
        return

    elif len(parsed_message) == 2:
        user, username = parse_user(parsed_message[1])
        if user:
            v_data = VolunteerSerializer(user).data
            msg = i18n["slack"]["user_info"].format(
                username, "\n".join(dict_to_table(v_data))
            )
        else:
            msg = i18n["slack"]["errors"]["unknown_username"].format(username=username)
    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)


def user_info_text(user: BlossomUser) -> str:
    """Get the info message for the given user."""
    general = user_general_info(user)

    return f"TODO\n{general}"


def user_general_info(user: BlossomUser) -> Dict:
    """Get general info for the given user."""
    total_gamma = user.gamma
    recent_gamma = user.gamma_at_time(start_time=timezone.now() - timedelta(weeks=2))
    gamma = f"{total_gamma} Γ ({recent_gamma} Γ in last 2 weeks)"
    joined_on = _format_time(user.date_joined)
    last_active = _format_time(user.date_last_active())

    return {
        "Gamma": gamma,
        "Joined on": joined_on,
        "Last active": last_active,
    }


def _format_time(time: datetime) -> str:
    """Format the given time in absolute and relative strings."""
    now = timezone.now()
    absolute = time.date().isoformat()

    relative_delta = now - time
    relative = _relative_duration(relative_delta)

    if now >= time:
        return f"{absolute} ({relative} ago)"
    else:
        return f"{absolute} (in {relative})"


def _relative_duration(delta: timedelta) -> str:
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
