from typing import Dict, List

from blossom.api.models import TranscriptionCheck
from blossom.api.slack.utils import get_source
from blossom.authentication.models import BlossomUser


def _get_check_base_text(check: TranscriptionCheck) -> str:
    """Get basic info about the transcription check."""
    transcription = check.transcription
    submission = transcription.submission
    user: BlossomUser = transcription.author
    username = user.username
    user_link = f"<https://reddit.com/u/{username}?sort=new|u/{username}>"
    is_nsfw = submission.nsfw
    # Get the gamma at the time of the transcription that is checked
    gamma = user.gamma_at_time(end_time=submission.complete_time)

    base_text = f"Transcription check for *{user_link}* ({gamma:,d} Γ):\n"

    # Add relevant links
    tor_url = (
        "<{}|ToR Post>".format(submission.tor_url) if submission.tor_url else "[N/A]"
    )
    post_url = "<{}|Partner Post>".format(submission.url) if submission.url else "[N/A]"
    transcription_url = (
        "<{}|Transcription>".format(transcription.url)
        if transcription.url
        else "[Removed]"
    )
    if transcription.removed_from_reddit and transcription.url:
        transcription_url += " [Removed]"

    source = get_source(submission)
    details = [tor_url, post_url, transcription_url, source]
    # Indicate if the post is NSFW
    if is_nsfw:
        details.append("[NSFW]")
    base_text += " | ".join(details) + "\n"

    # Add check trigger
    trigger = check.trigger or "_Not specified_"
    base_text += f"Trigger: {trigger}\n"

    # Is it the first transcription? Extra care has to be taken
    if gamma == 1:
        base_text += ":rotating_light: First transcription! :rotating_light:"

    return base_text


def _get_check_unclaimed_actions(check: TranscriptionCheck) -> List[Dict]:
    """Get the action buttons for an unclaimed check."""
    return [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Claim"},
            "value": f"check_claim_{check.id}",
        }
    ]


def _get_check_pending_actions(check: TranscriptionCheck) -> List[Dict]:
    """Get the action buttons for a pending check."""
    return [
        {
            "type": "button",
            "style": "primary",
            "text": {"type": "plain_text", "text": "Approve"},
            "value": f"check_approved_{check.id}",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Comment"},
            "value": f"check_comment-pending_{check.id}",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Warn"},
            "value": f"check_warning-pending_{check.id}",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Unclaim"},
            "value": f"check_unclaim_{check.id}",
        },
    ]


def _get_check_approved_actions(check: TranscriptionCheck) -> List[Dict]:
    """Get the action buttons for an approved check."""
    return [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Revert"},
            "value": f"check_pending_{check.id}",
        },
    ]


def _get_check_comment_pending_actions(check: TranscriptionCheck) -> List[Dict]:
    """Get the action buttons for a check with pending comment."""
    return [
        {
            "type": "button",
            "style": "primary",
            "text": {"type": "plain_text", "text": "Resolve"},
            "value": f"check_comment-resolved_{check.id}",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Not fixed"},
            "value": f"check_comment-unfixed_{check.id}",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Revert"},
            "value": f"check_pending_{check.id}",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Unclaim"},
            "value": f"check_unclaim_{check.id}",
        },
    ]


def _get_check_comment_resolved_actions(check: TranscriptionCheck) -> List[Dict]:
    """Get the action buttons for a check with resolved comment."""
    return [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Revert"},
            "value": f"check_comment-pending_{check.id}",
        },
    ]


def _get_check_comment_unfixed_actions(check: TranscriptionCheck) -> List[Dict]:
    """Get the action buttons for a check with unfixed comment."""
    return [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Revert"},
            "value": f"check_comment-pending_{check.id}",
        },
    ]


def _get_check_warning_pending_actions(check: TranscriptionCheck) -> List[Dict]:
    """Get the action buttons for a check with pending warning."""
    return [
        {
            "type": "button",
            "style": "primary",
            "text": {"type": "plain_text", "text": "Resolve"},
            "value": f"check_warning-resolved_{check.id}",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Not fixed"},
            "value": f"check_warning-unfixed_{check.id}",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Revert"},
            "value": f"check_pending_{check.id}",
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Unclaim"},
            "value": f"check_unclaim_{check.id}",
        },
    ]


def _get_check_warning_resolved_actions(check: TranscriptionCheck) -> List[Dict]:
    """Get the action buttons for a check with resolved warning."""
    return [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Revert"},
            "value": f"check_warning-pending_{check.id}",
        },
    ]


def _get_check_warning_unfixed_actions(check: TranscriptionCheck) -> List[Dict]:
    """Get the action buttons for a check with unfixed warning."""
    return [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Revert"},
            "value": f"check_warning-pending_{check.id}",
        },
    ]


def _get_check_actions(check: TranscriptionCheck) -> List[Dict]:
    """Get the action buttons for the check."""
    check_status = TranscriptionCheck.TranscriptionCheckStatus

    if check.moderator is None:
        return _get_check_unclaimed_actions(check)
    if check.status == check_status.PENDING:
        return _get_check_pending_actions(check)
    if check.status == check_status.APPROVED:
        return _get_check_approved_actions(check)
    if check.status == check_status.COMMENT_PENDING:
        return _get_check_comment_pending_actions(check)
    if check.status == check_status.COMMENT_RESOLVED:
        return _get_check_comment_resolved_actions(check)
    if check.status == check_status.COMMENT_UNFIXED:
        return _get_check_comment_unfixed_actions(check)
    if check.status == check_status.WARNING_PENDING:
        return _get_check_warning_pending_actions(check)
    if check.status == check_status.WARNING_RESOLVED:
        return _get_check_warning_resolved_actions(check)
    if check.status == check_status.WARNING_UNFIXED:
        return _get_check_warning_unfixed_actions(check)

    raise RuntimeError(f"Unexpected transcription check status: {check.status}")


def _get_check_status_text(check: TranscriptionCheck) -> str:
    """Get a text indicating the status of the transcription check."""
    check_status = TranscriptionCheck.TranscriptionCheckStatus
    mod_username = "u/" + check.moderator.username if check.moderator else None

    status = (
        "*Unclaimed*"
        if check.moderator is None
        else f"*Claimed* by {mod_username}"
        if check.status == check_status.PENDING
        else f"*Approved* by {mod_username}"
        if check.status == check_status.APPROVED
        else f"*Comment pending* by {mod_username}"
        if check.status == check_status.COMMENT_PENDING
        else f"*Comment resolved* by {mod_username}"
        if check.status == check_status.COMMENT_RESOLVED
        else f"*Comment unfixed* by {mod_username}"
        if check.status == check_status.COMMENT_UNFIXED
        else f"*Warning pending* by {mod_username}"
        if check.status == check_status.WARNING_PENDING
        else f"*Warning resolved* by {mod_username}"
        if check.status == check_status.WARNING_RESOLVED
        else f"*Warning unfixed* by {mod_username}"
        if check.status == check_status.WARNING_UNFIXED
        else f"_INVALID:_ {check.status}"
    )

    return f"Status: {status}"


def construct_transcription_check_blocks(check: TranscriptionCheck) -> List[Dict]:
    """Construct the Slack blocks for the transcription check message."""
    submission = check.transcription.submission
    is_nsfw = submission.nsfw

    base_text = _get_check_base_text(check)
    actions = _get_check_actions(check)
    status_text = _get_check_status_text(check)
    text = f"{base_text}\n{status_text}"

    text_section = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": text},
    }

    # Add image preview if the post is not NSFW
    if not is_nsfw:
        text_section["accessory"] = {
            "type": "image",
            "image_url": submission.content_url,
            "alt_text": f"Image of submission {submission.id}",
        }

    return [
        text_section,
        {"type": "divider"},
        {"type": "actions", "elements": actions},
    ]
