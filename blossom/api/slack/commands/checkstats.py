from datetime import timedelta
from typing import Dict

from django.db.models import Q, QuerySet
from django.utils import timezone

from blossom.api.models import TranscriptionCheck
from blossom.api.slack import client
from blossom.api.slack.commands.utils import format_stats_section, format_time
from blossom.api.slack.utils import parse_user
from blossom.authentication.models import BlossomUser
from blossom.strings import translation

i18n = translation()

CheckStatus = TranscriptionCheck.TranscriptionCheckStatus

# Timedelta for all "recent" queries
RECENT_DELTA = timedelta(weeks=2)


def checkstats_cmd(channel: str, message: str) -> None:
    """Get the check stats for a specific mod.

    Notably this shows how many transcriptions the given mod checked,
    NOT how many checks were done for the given user.
    """
    parsed_message = message.split()

    if len(parsed_message) == 1:
        # they didn't give a username
        msg = i18n["slack"]["errors"]["missing_username"]
    elif len(parsed_message) == 2:
        user, username = parse_user(parsed_message[1])
        if user:
            msg = check_stats_msg(user)
        else:
            msg = i18n["slack"]["errors"]["unknown_username"].format(username=username)

    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)


def check_stats_msg(mod: BlossomUser) -> str:
    """Get the message showing the check stats for the given mod."""
    recent_date = timezone.now() - RECENT_DELTA

    server_checks = TranscriptionCheck.objects.filter(complete_time__isnull=False)
    mod_checks = server_checks.filter(moderator=mod)

    recent_server_checks = server_checks.filter(complete_time__gte=recent_date)
    recent_mod_checks = mod_checks.filter(complete_time__gte=recent_date)

    name_link = f"<https://reddit.com/u/{mod.username}|u/{mod.username}>"
    title = f"Mod check stats for *{name_link}*:"

    all_stats = format_stats_section(
        "Completed Checks",
        _all_check_stats(
            server_checks, mod_checks, recent_server_checks, recent_mod_checks
        ),
    )
    warning_stats = format_stats_section(
        "Completed Warnings",
        _warning_check_stats(
            server_checks, mod_checks, recent_server_checks, recent_mod_checks
        ),
    )
    comment_stats = format_stats_section(
        "Completed Comments",
        _comment_check_stats(
            server_checks, mod_checks, recent_server_checks, recent_mod_checks
        ),
    )

    return f"{title}\n\n{all_stats}\n\n{warning_stats}\n\n{comment_stats}"


def _all_check_stats(
    server_checks: QuerySet,
    mod_checks: QuerySet,
    recent_server_checks: QuerySet,
    recent_mod_checks: QuerySet,
) -> Dict:
    """Get the stats for all checks."""
    # All time checks
    server_check_count = server_checks.count()
    mod_check_count = mod_checks.count()
    check_ratio = _get_ratio(mod_check_count, server_check_count)
    check_msg = f"{mod_check_count} ({check_ratio:.1%} of all checks)"

    # Recent checks
    recent_server_check_count = recent_server_checks.count()
    recent_mod_check_count = recent_mod_checks.count()
    recent_check_ratio = _get_ratio(recent_mod_check_count, recent_server_check_count)
    recent_check_msg = (
        f"{recent_mod_check_count} ({recent_check_ratio:.1%} of all recent checks)"
    )

    # Last check
    last_check = mod_checks.order_by("-complete_time").first()
    last_check_date = last_check.complete_time if last_check else None
    last_check_msg = format_time(last_check_date)

    return {
        "All-time": check_msg,
        "Last 2 weeks": recent_check_msg,
        "Last completed": last_check_msg,
    }


def _warning_check_stats(
    server_checks: QuerySet,
    mod_checks: QuerySet,
    recent_server_checks: QuerySet,
    recent_mod_checks: QuerySet,
) -> Dict:
    """Get the stats for the warning checks."""
    warning_filter = (
        Q(status=CheckStatus.WARNING_PENDING)
        | Q(status=CheckStatus.WARNING_RESOLVED)
        | Q(status=CheckStatus.WARNING_UNFIXED)
    )
    server_warnings = server_checks.filter(warning_filter)
    mod_warnings = mod_checks.filter(warning_filter)

    # All time warnings
    server_warning_count = server_warnings.count()
    mod_warning_count = mod_warnings.count()
    warning_ratio_checks = _get_ratio(mod_warning_count, mod_checks.count())
    warning_ratio_all = _get_ratio(mod_warning_count, server_warning_count)
    warning_msg = (
        f"{mod_warning_count} ({warning_ratio_checks:.1%} of checks, "
        f"{warning_ratio_all:.1%} of all warnings)"
    )

    # Recent warnings
    recent_server_warning_count = recent_server_checks.filter(warning_filter).count()
    recent_mod_warning_count = recent_mod_checks.filter(warning_filter).count()
    recent_warning_ratio_checks = _get_ratio(
        recent_mod_warning_count, recent_mod_checks.count()
    )
    recent_warning_ratio_all = _get_ratio(
        recent_mod_warning_count, recent_server_warning_count
    )
    recent_warning_msg = (
        f"{recent_mod_warning_count} "
        f"({recent_warning_ratio_checks:.1%} of recent checks, "
        f"{recent_warning_ratio_all:.1%} of all recent warnings)"
    )

    # Last warning
    last_warning = mod_warnings.order_by("-complete_time").first()
    last_warning_date = last_warning.complete_time if last_warning else None
    last_warning_msg = format_time(last_warning_date)

    return {
        "All-time": warning_msg,
        "Last 2 weeks": recent_warning_msg,
        "Last completed": last_warning_msg,
    }


def _comment_check_stats(
    server_checks: QuerySet,
    mod_checks: QuerySet,
    recent_server_checks: QuerySet,
    recent_mod_checks: QuerySet,
) -> Dict:
    """Get the stats for the comment checks."""
    comment_filter = (
        Q(status=CheckStatus.COMMENT_PENDING)
        | Q(status=CheckStatus.COMMENT_RESOLVED)
        | Q(status=CheckStatus.COMMENT_UNFIXED)
    )
    server_comments = server_checks.filter(comment_filter)
    mod_comments = mod_checks.filter(comment_filter)

    # All time comments
    server_comment_count = server_comments.count()
    mod_comment_count = mod_comments.count()
    comment_ratio_checks = _get_ratio(mod_comment_count, mod_checks.count())
    comment_ratio_all = _get_ratio(mod_comment_count, server_comment_count)
    comment_msg = (
        f"{mod_comment_count} ({comment_ratio_checks:.1%} of checks, "
        f"{comment_ratio_all:.1%} of all comments)"
    )

    # Recent comments
    recent_server_comment_count = recent_server_checks.filter(comment_filter).count()
    recent_mod_comment_count = recent_mod_checks.filter(comment_filter).count()
    recent_comment_ratio_checks = _get_ratio(
        recent_mod_comment_count, recent_mod_checks.count()
    )
    recent_comment_ratio_all = _get_ratio(
        recent_mod_comment_count, recent_server_comment_count
    )
    recent_comment_msg = (
        f"{recent_mod_comment_count} "
        f"({recent_comment_ratio_checks:.1%} of recent checks, "
        f"{recent_comment_ratio_all:.1%} of all recent comments)"
    )

    # Last comment
    last_comment = mod_comments.order_by("-complete_time").first()
    last_comment_date = last_comment.complete_time if last_comment else None
    last_comment_msg = format_time(last_comment_date)

    return {
        "All-time": comment_msg,
        "Last 2 weeks": recent_comment_msg,
        "Last completed": last_comment_msg,
    }


def _get_ratio(value: float, total: float) -> float:
    """Get the ratio of the two values.

    Returns 0.0 if the total is 0.0.
    """
    return value / total if total > 0 else 0.0
