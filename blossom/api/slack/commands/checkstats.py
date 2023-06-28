from datetime import datetime, timedelta
from typing import Dict

from django.db.models import Q, QuerySet
from django.utils import timezone

from blossom.api.models import Submission, TranscriptionCheck
from blossom.api.slack import client
from blossom.api.slack.commands.utils import format_stats_section, format_time
from blossom.api.slack.utils import parse_user
from blossom.authentication.models import BlossomUser
from blossom.strings import translation

i18n = translation()

CheckStatus = TranscriptionCheck.TranscriptionCheckStatus

# Timedelta for all "recent" queries
RECENT_DELTA = timedelta(weeks=2)

WARNING_FILTER = (
    Q(status=CheckStatus.WARNING_PENDING)
    | Q(status=CheckStatus.WARNING_RESOLVED)
    | Q(status=CheckStatus.WARNING_UNFIXED)
)

COMMENT_FILTER = (
    Q(status=CheckStatus.COMMENT_PENDING)
    | Q(status=CheckStatus.COMMENT_RESOLVED)
    | Q(status=CheckStatus.COMMENT_UNFIXED)
)


def checkstats_cmd(channel: str, message: str) -> None:
    """Get the check stats for a specific mod.

    Notably this shows how many transcriptions the given mod checked,
    NOT how many checks were done for the given user.
    """
    parsed_message = message.split()

    if len(parsed_message) == 1:
        # they didn't give a username
        msg = check_stats_all_msg()
    elif len(parsed_message) == 2:
        user, username = parse_user(parsed_message[1])
        if user:
            msg = check_stats_mod_msg(user)
        else:
            msg = i18n["slack"]["errors"]["unknown_username"].format(username=username)

    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)


def check_stats_mod_msg(mod: BlossomUser) -> str:
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
        _all_check_stats(server_checks, mod_checks, recent_server_checks, recent_mod_checks),
    )
    warning_stats = format_stats_section(
        "Completed Warnings",
        _warning_check_stats(server_checks, mod_checks, recent_server_checks, recent_mod_checks),
    )
    comment_stats = format_stats_section(
        "Completed Comments",
        _comment_check_stats(server_checks, mod_checks, recent_server_checks, recent_mod_checks),
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
    recent_check_msg = f"{recent_mod_check_count} ({recent_check_ratio:.1%} of all recent checks)"

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
    server_warnings = server_checks.filter(WARNING_FILTER)
    mod_warnings = mod_checks.filter(WARNING_FILTER)

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
    recent_server_warning_count = recent_server_checks.filter(WARNING_FILTER).count()
    recent_mod_warning_count = recent_mod_checks.filter(WARNING_FILTER).count()
    recent_warning_ratio_checks = _get_ratio(recent_mod_warning_count, recent_mod_checks.count())
    recent_warning_ratio_all = _get_ratio(recent_mod_warning_count, recent_server_warning_count)
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
    server_comments = server_checks.filter(COMMENT_FILTER)
    mod_comments = mod_checks.filter(COMMENT_FILTER)

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
    recent_server_comment_count = recent_server_checks.filter(COMMENT_FILTER).count()
    recent_mod_comment_count = recent_mod_checks.filter(COMMENT_FILTER).count()
    recent_comment_ratio_checks = _get_ratio(recent_mod_comment_count, recent_mod_checks.count())
    recent_comment_ratio_all = _get_ratio(recent_mod_comment_count, recent_server_comment_count)
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


def check_stats_all_msg() -> str:
    """Get the check stats for all mods together."""
    now = datetime.now(tz=timezone.utc)

    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(weeks=1)
    one_month_ago = now - timedelta(days=30)
    one_year_ago = now - timedelta(days=365)

    # Transcriptions

    query_transcribed_all = Submission.objects.filter(
        removed_from_queue=False, completed_by__isnull=False
    )

    transcribed_all = query_transcribed_all.count()
    transcribed_one_day = query_transcribed_all.filter(complete_time__gte=one_day_ago).count()
    transcribed_one_week = query_transcribed_all.filter(complete_time__gte=one_week_ago).count()
    transcribed_one_month = query_transcribed_all.filter(complete_time__gte=one_month_ago).count()
    transcribed_one_year = query_transcribed_all.filter(complete_time__gte=one_year_ago).count()

    query_checks_all = TranscriptionCheck.objects.filter(complete_time__isnull=False)

    # Checks

    checks_all = query_checks_all.count()
    checks_percentage_all = _get_ratio(checks_all, transcribed_all)
    checks_one_day = query_checks_all.filter(complete_time__gte=one_day_ago).count()
    checks_percentage_one_day = _get_ratio(checks_one_day, transcribed_one_day)
    checks_one_week = query_checks_all.filter(complete_time__gte=one_week_ago).count()
    checks_percentage_one_week = _get_ratio(checks_one_week, transcribed_one_week)
    checks_one_month = query_checks_all.filter(complete_time__gte=one_month_ago).count()
    checks_percentage_one_month = _get_ratio(checks_one_month, transcribed_one_month)
    checks_one_year = query_checks_all.filter(complete_time__gte=one_year_ago).count()
    checks_percentage_one_year = _get_ratio(checks_one_year, transcribed_one_year)

    check_info = i18n["slack"]["checkstats"]["check_info"].format(
        checks_all=checks_all,
        checks_percentage_all=checks_percentage_all,
        checks_one_day=checks_one_day,
        checks_percentage_one_day=checks_percentage_one_day,
        checks_one_week=checks_one_week,
        checks_percentage_one_week=checks_percentage_one_week,
        checks_one_month=checks_one_month,
        checks_percentage_one_month=checks_percentage_one_month,
        checks_one_year=checks_one_year,
        checks_percentage_one_year=checks_percentage_one_year,
    )

    # Warnings

    query_warnings_all = query_checks_all.filter(WARNING_FILTER)

    warnings_all = query_warnings_all.count()
    warnings_percentage_all = _get_ratio(warnings_all, checks_all)
    warnings_one_day = query_warnings_all.filter(complete_time__gte=one_day_ago).count()
    warnings_percentage_one_day = _get_ratio(warnings_one_day, checks_one_day)
    warnings_one_week = query_warnings_all.filter(complete_time__gte=one_week_ago).count()
    warnings_percentage_one_week = _get_ratio(warnings_one_week, checks_one_week)
    warnings_one_month = query_warnings_all.filter(complete_time__gte=one_month_ago).count()
    warnings_percentage_one_month = _get_ratio(warnings_one_month, checks_one_month)
    warnings_one_year = query_warnings_all.filter(complete_time__gte=one_year_ago).count()
    warnings_percentage_one_year = _get_ratio(warnings_one_year, checks_one_year)

    warning_info = i18n["slack"]["checkstats"]["warning_info"].format(
        warnings_all=warnings_all,
        warnings_percentage_all=warnings_percentage_all,
        warnings_one_day=warnings_one_day,
        warnings_percentage_one_day=warnings_percentage_one_day,
        warnings_one_week=warnings_one_week,
        warnings_percentage_one_week=warnings_percentage_one_week,
        warnings_one_month=warnings_one_month,
        warnings_percentage_one_month=warnings_percentage_one_month,
        warnings_one_year=warnings_one_year,
        warnings_percentage_one_year=warnings_percentage_one_year,
    )

    # Comments

    query_comments_all = query_checks_all.filter(COMMENT_FILTER)

    comments_all = query_comments_all.count()
    comments_percentage_all = _get_ratio(comments_all, checks_all)
    comments_one_day = query_comments_all.filter(complete_time__gte=one_day_ago).count()
    comments_percentage_one_day = _get_ratio(comments_one_day, checks_one_day)
    comments_one_week = query_comments_all.filter(complete_time__gte=one_week_ago).count()
    comments_percentage_one_week = _get_ratio(comments_one_week, checks_one_week)
    comments_one_month = query_comments_all.filter(complete_time__gte=one_month_ago).count()
    comments_percentage_one_month = _get_ratio(comments_one_month, checks_one_month)
    comments_one_year = query_comments_all.filter(complete_time__gte=one_year_ago).count()
    comments_percentage_one_year = _get_ratio(comments_one_year, checks_one_year)

    comment_info = i18n["slack"]["checkstats"]["comment_info"].format(
        comments_all=comments_all,
        comments_percentage_all=comments_percentage_all,
        comments_one_day=comments_one_day,
        comments_percentage_one_day=comments_percentage_one_day,
        comments_one_week=comments_one_week,
        comments_percentage_one_week=comments_percentage_one_week,
        comments_one_month=comments_one_month,
        comments_percentage_one_month=comments_percentage_one_month,
        comments_one_year=comments_one_year,
        comments_percentage_one_year=comments_percentage_one_year,
    )

    # Putting it together

    return i18n["slack"]["checkstats"]["message"].format(
        check_info=check_info,
        warning_info=warning_info,
        comment_info=comment_info,
    )


def _get_ratio(value: float, total: float) -> float:
    """Get the ratio of the two values.

    Returns 0.0 if the total is 0.0.
    """
    return value / total if total > 0 else 0.0
