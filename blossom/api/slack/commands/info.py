from datetime import datetime, timedelta
from typing import Dict

from django.utils import timezone

from blossom.api.models import Submission, TranscriptionCheck
from blossom.api.slack import client
from blossom.api.slack.commands.utils import bool_str, format_stats_section, format_time
from blossom.api.slack.utils import dict_to_table, parse_user
from blossom.api.views.misc import Summary
from blossom.authentication.models import BlossomUser
from blossom.strings import translation

i18n = translation()


QUEUE_TIMEOUT = timedelta(hours=18)


def info_cmd(channel: str, message: str) -> None:
    """Send info about a user to slack."""
    parsed_message = message.split()
    if len(parsed_message) == 1:
        # they just sent an empty info message, get info about the whole project
        client.chat_postMessage(
            channel=channel,
            text=all_info_text(),
        )
        return

    elif len(parsed_message) == 2:
        user, username = parse_user(parsed_message[1])
        if user:
            msg = user_info_text(user)
        else:
            msg = i18n["slack"]["errors"]["unknown_username"].format(username=username)
    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)


def user_info_text(user: BlossomUser) -> str:
    """Get the info message for the given user."""
    name_link = f"<https://reddit.com/u/{user.username}|u/{user.username}>"
    title = f"Info about *{name_link}*:"

    general = format_stats_section("General", user_general_info(user))
    transcription_quality = format_stats_section(
        "Transcription Quality", user_transcription_quality_info(user)
    )
    debug = format_stats_section("Debug Info", user_debug_info(user))

    return f"{title}\n\n{general}\n\n{transcription_quality}\n\n{debug}"


def user_general_info(user: BlossomUser) -> Dict:
    """Get general info for the given user."""
    total_gamma = user.gamma
    recent_gamma = user.gamma_at_time(start_time=timezone.now() - timedelta(weeks=2))
    gamma = f"{total_gamma} Γ ({recent_gamma} Γ in last 2 weeks)"
    joined_on = format_time(user.date_joined)
    last_active = format_time(user.date_last_active()) or "Never"

    return {
        "Gamma": gamma,
        "Joined on": joined_on,
        "Last active": last_active,
    }


def user_transcription_quality_info(user: BlossomUser) -> Dict:
    """Get info about the transcription quality of the given user."""
    gamma = user.gamma
    check_status = TranscriptionCheck.TranscriptionCheckStatus

    # The checks for the given user
    user_checks = TranscriptionCheck.objects.filter(transcription__author=user)
    check_count = user_checks.count()
    check_ratio = check_count / gamma if gamma > 0 else 0
    checks = f"{check_count} ({check_ratio:.1%} of transcriptions)"

    # The comments for the given user
    user_comments_pending = user_checks.filter(status=check_status.COMMENT_PENDING)
    user_comments_resolved = user_checks.filter(status=check_status.COMMENT_RESOLVED)
    user_comments_unfixed = user_checks.filter(status=check_status.COMMENT_UNFIXED)
    comments_count = (
        user_comments_pending.count()
        + user_comments_resolved.count()
        + user_comments_unfixed.count()
    )
    comments_ratio = comments_count / check_count if check_count > 0 else 0
    comments = f"{comments_count} ({comments_ratio:.1%} of checks)"

    # The warnings for the given user
    user_warnings_pending = user_checks.filter(status=check_status.WARNING_PENDING)
    user_warnings_resolved = user_checks.filter(status=check_status.WARNING_RESOLVED)
    user_warnings_unfixed = user_checks.filter(status=check_status.WARNING_UNFIXED)
    warnings_count = (
        user_warnings_pending.count()
        + user_warnings_resolved.count()
        + user_warnings_unfixed.count()
    )
    warnings_ratio = warnings_count / check_count if check_count > 0 else 0
    warnings = f"{warnings_count} ({warnings_ratio:.1%} of checks)"

    # Watch status
    watch_status = user.transcription_check_reason(ignore_low_activity=True)

    return {
        "Checks": checks,
        "Warnings": warnings,
        "Comments": comments,
        "Watch status": watch_status,
    }


def user_debug_info(user: BlossomUser) -> Dict:
    """Get debug info about the given user."""
    user_id = f"`{user.id}`"
    blocked = bool_str(user.blocked)
    bot = bool_str(user.is_bot)
    accepted_coc = bool_str(user.accepted_coc)

    return {
        "ID": user_id,
        "Blocked": blocked,
        "Bot": bot,
        "Accepted CoC": accepted_coc,
    }


def all_info_text() -> str:
    """Get the info message for all users."""
    now = datetime.now(tz=timezone.utc)

    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(weeks=1)
    two_weeks_ago = now - timedelta(weeks=2)
    one_month_ago = now - timedelta(days=30)
    one_year_ago = now - timedelta(days=365)

    queue_timeout = now - QUEUE_TIMEOUT

    # Submission info

    query_all = Submission.objects.filter(removed_from_queue=False)
    query_one_day = query_all.filter(create_time__gte=one_day_ago)
    query_one_week = query_all.filter(create_time__gte=one_week_ago)
    query_one_month = query_all.filter(create_time__gte=one_month_ago)
    query_one_year = query_all.filter(create_time__gte=one_year_ago)

    query_all_queue = query_all.filter(create_time__gte=queue_timeout, archived=False)

    total_all = query_all.count()
    total_one_day = query_one_day.count()
    total_one_week = query_one_week.count()
    total_one_month = query_one_month.count()
    total_one_year = query_one_year.count()

    queue_all = query_all_queue.count()

    submission_info = i18n["slack"]["info"]["submission_info"].format(
        total_all=total_all,
        queue_all=queue_all,
        total_one_day=total_one_day,
        total_one_week=total_one_week,
        total_one_month=total_one_month,
        total_one_year=total_one_year,
    )

    # Transcription info

    transcribed_all = query_all.filter(completed_by__isnull=False).count()
    transcribed_percentage_all = transcribed_all / total_all
    transcribed_one_day = query_one_day.filter(completed_by__isnull=False).count()
    transcribed_percentage_one_day = transcribed_one_day / total_one_day
    transcribed_one_week = query_one_week.filter(completed_by__isnull=False).count()
    transcribed_percentage_one_week = transcribed_one_week / total_one_week
    transcribed_one_month = query_one_month.filter(completed_by__isnull=False).count()
    transcribed_percentage_one_month = transcribed_one_month / total_one_month
    transcribed_one_year = query_one_year.filter(completed_by__isnull=False).count()
    transcribed_percentage_one_year = transcribed_one_year / total_one_year

    transcription_info = i18n["slack"]["info"]["transcription_info"].format(
        transcribed_all=transcribed_all,
        transcribed_percentage_all=transcribed_percentage_all,
        transcribed_one_day=transcribed_one_day,
        transcribed_percentage_one_day=transcribed_percentage_one_day,
        transcribed_one_week=transcribed_one_week,
        transcribed_percentage_one_week=transcribed_percentage_one_week,
        transcribed_one_month=transcribed_one_month,
        transcribed_percentage_one_month=transcribed_percentage_one_month,
        transcribed_one_year=transcribed_one_year,
        transcribed_percentage_one_year=transcribed_percentage_one_year,
    )

    # Volunteer info

    query_volunteers = BlossomUser.objects.filter(is_bot=False)

    volunteers_all = query_volunteers.count()
    volunteers_new_one_day = query_volunteers.filter(date_joined__gte=one_day_ago).count()
    volunteers_new_one_week = query_volunteers.filter(date_joined__gte=one_week_ago).count()
    volunteers_new_one_month = query_volunteers.filter(date_joined__gte=one_month_ago).count()
    volunteers_new_one_year = query_volunteers.filter(date_joined__gte=one_year_ago).count()

    volunteers_active_two_weeks = (
        Submission.objects.filter(
            completed_by__isnull=False,
            complete_time__gte=two_weeks_ago,
        )
        .values("completed_by")
        .distinct()
        .count()
    )

    volunteer_info = i18n["slack"]["info"]["volunteer_info"].format(
        volunteers_all=volunteers_all,
        volunteers_new_one_day=volunteers_new_one_day,
        volunteers_new_one_week=volunteers_new_one_week,
        volunteers_new_one_month=volunteers_new_one_month,
        volunteers_new_one_year=volunteers_new_one_year,
        volunteers_active_two_weeks=volunteers_active_two_weeks,
    )

    # Putting it all together
    return i18n["slack"]["info"]["message"].format(
        submission_info=submission_info,
        transcription_info=transcription_info,
        volunteer_info=volunteer_info,
    )
