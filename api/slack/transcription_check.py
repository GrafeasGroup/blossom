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

    # Add check reason
    # base_text += f"Reason: {reason}\n"

    # Is it the first transcription? Extra care has to be taken
    if gamma == 1:
        base_text += ":rotating_light: First transcription! :rotating_light:"

    return base_text


def _construct_transcription_check_blocks(check: TranscriptionCheck) -> List[Dict]:
    """Construct the Slack blocks for the transcription check message."""
    submission = check.transcription.submission

    base_text = _get_check_base_text(check)

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
    ]
