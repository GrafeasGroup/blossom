from datetime import datetime
from typing import List

from blossom.api.models import TranscriptionCheck
from blossom.api.slack import client
from blossom.api.slack.utils import get_source, parse_user
from blossom.authentication.models import BlossomUser
from blossom.strings import translation

i18n = translation()


def _warning_entry(check: TranscriptionCheck) -> str:
    """Get the list entry for a single check."""
    check_url = check.get_slack_url()

    transcription = check.transcription
    tr_url = transcription.url

    time: datetime = transcription.create_time
    date = time.date().isoformat()

    submission = transcription.submission
    source = get_source(submission)

    return i18n["slack"]["warnings"]["warning_entry"].format(
        date=date, source=source, check_url=check_url, tr_url=tr_url
    )


def _get_warning_checks(user: BlossomUser) -> List[TranscriptionCheck]:
    """Get all warnings for the given user."""
    # Get all warning checks
    pending_warnings = TranscriptionCheck.objects.filter(
        transcription__author=user,
        status=TranscriptionCheck.TranscriptionCheckStatus.WARNING_PENDING,
    )
    resolved_warnings = TranscriptionCheck.objects.filter(
        transcription__author=user,
        status=TranscriptionCheck.TranscriptionCheckStatus.WARNING_RESOLVED,
    )
    unfixed_warnings = TranscriptionCheck.objects.filter(
        transcription__author=user,
        status=TranscriptionCheck.TranscriptionCheckStatus.WARNING_UNFIXED,
    )

    # Aggregate the warnings and sort them by the transcription date
    warnings: List[TranscriptionCheck] = (
        list(pending_warnings) + list(resolved_warnings) + list(unfixed_warnings)
    )
    warnings.sort(key=lambda ch: ch.transcription.create_time)

    return warnings


def _warning_text(user: BlossomUser) -> str:
    """Get the text for the warnings for the given user."""
    username = user.username
    warnings = _get_warning_checks(user)

    # Check if there are any warnings
    if len(warnings) == 0:
        return i18n["slack"]["warnings"]["no_warnings"].format(username=username)

    # Format every entry
    entries = [_warning_entry(ch) for ch in warnings]
    warning_list = "\n".join(entries)

    return i18n["slack"]["warnings"]["warnings"].format(
        username=username, count=len(warnings), warning_list=warning_list
    )


def warnings_cmd(channel: str, message: str) -> None:
    """List the warnings for a given user."""
    parsed_message = message.split()

    if len(parsed_message) == 1:
        # they didn't give a username
        msg = i18n["slack"]["errors"]["missing_username"]
    elif len(parsed_message) <= 3:
        user, username = parse_user(parsed_message[1])
        if user:
            msg = _warning_text(user)
        else:
            msg = i18n["slack"]["errors"]["unknown_username"].format(username=username)
    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(
        channel=channel, text=msg, unfurl_links=False, unfurl_media=False
    )
