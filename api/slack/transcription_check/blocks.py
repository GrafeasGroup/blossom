from typing import Dict, List

from api.models import TranscriptionCheck


def _get_check_base_text(check: TranscriptionCheck) -> str:
    """Get basic info about the transcription check."""
    transcription = check.transcription
    submission = transcription.submission
    user = transcription.author
    gamma = user.gamma

    base_text = f"*Transcription check* for u/{user.username} ({user.gamma:,d} Γ):\n"

    # Add relevant links
    tor_url = (
        "<{}|ToR Post>".format(submission.tor_url) if submission.tor_url else "[N/A]"
    )
    post_url = "<{}|Partner Post>".format(submission.url) if submission.url else "[N/A]"
    transcription_url = (
        "<{}|Transcription>".format(transcription.url)
        if transcription.url and not transcription.removed_from_reddit
        else "[Removed]"
    )
    base_text += " | ".join([tor_url, post_url, transcription_url]) + "\n"

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
            "value": f"check_approve_{check.id}",
        },
        {
            "type": "button",
            "style": "default",
            "text": {"type": "plain_text", "text": "Comment"},
            "value": f"check_comment-create_{check.id}",
        },
        {
            "type": "button",
            "style": "danger",
            "text": {"type": "plain_text", "text": "Warn"},
            "value": f"check_warn-create_{check.id}",
        },
        {
            "type": "button",
            "style": "default",
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
            "value": f"check_approve-revert_{check.id}",
        },
    ]


def _get_check_comment_pending_actions(check: TranscriptionCheck) -> List[Dict]:
    """Get the action buttons for a check with pending comment."""
    return [
        {
            "type": "button",
            "style": "primary",
            "text": {"type": "plain_text", "text": "Resolve"},
            "value": f"check_comment-resolve_{check.id}",
        },
        {
            "type": "button",
            "style": "default",
            "text": {"type": "plain_text", "text": "Revert"},
            "value": f"check_comment-revert_{check.id}",
        },
        {
            "type": "button",
            "style": "danger",
            "text": {"type": "plain_text", "text": "Warn"},
            "value": f"check_warn-create_{check.id}",
        },
        {
            "type": "button",
            "style": "default",
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
            "value": f"check_comment-revert_{check.id}",
        },
    ]


def _get_check_warning_pending_actions(check: TranscriptionCheck) -> List[Dict]:
    """Get the action buttons for a check with pending warning."""
    return [
        {
            "type": "button",
            "style": "primary",
            "text": {"type": "plain_text", "text": "Resolve"},
            "value": f"check_warn-resolve_{check.id}",
        },
        {
            "type": "button",
            "style": "default",
            "text": {"type": "plain_text", "text": "Revert"},
            "value": f"check_warn-revert_{check.id}",
        },
        {
            "type": "button",
            "style": "default",
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
            "value": f"check_warn-revert_{check.id}",
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
    if check.status == check_status.WARNING_PENDING:
        return _get_check_warning_pending_actions(check)
    if check.status == check_status.WARNING_RESOLVED:
        return _get_check_warning_resolved_actions(check)

    raise RuntimeError(f"Unexpected transcription check status: {check.status}")


def construct_transcription_check_blocks(check: TranscriptionCheck) -> List[Dict]:
    """Construct the Slack blocks for the transcription check message."""
    submission = check.transcription.submission

    base_text = _get_check_base_text(check)
    actions = _get_check_actions(check)

    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": base_text},
            "accessory": {
                "type": "image",
                "image_url": submission.content_url,
                "alt_text": f"Image of submission {submission.id}",
            },
        },
        {"type": "actions", "elements": actions},
    ]
