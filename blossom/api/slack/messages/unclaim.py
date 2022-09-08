from typing import List, Dict

from blossom.api.models import Submission
from blossom.api.slack.utils import get_source
from blossom.authentication.models import BlossomUser


def get_ask_confirmation_blocks(
    submission: Submission, user: BlossomUser
) -> List[Dict]:
    """Get the Slack message blocks for the message asking for confirmation."""
    text_block = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": get_ask_confirmation_text(),
        },
    }

    return [
        text_block,
        _get_submission_info_block(submission, user),
        {"type": "divider"},
        _get_ask_confirmation_buttons_block(submission),
    ]


def get_ask_confirmation_text() -> str:
    """Get the text asking the mod to confirm the unclaiming."""
    return "Do you really want to forcably unclaim the following submission?"


def get_confirm_blocks(submission: Submission, user: BlossomUser) -> List[Dict]:
    """Get the Slack message blocks when the unclaiming has been confirmed."""
    text_block = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": get_confirm_text(),
        },
    }

    return [
        text_block,
        _get_submission_info_block(submission, user),
    ]


def get_confirm_text() -> str:
    """Get the text for when the unclaiming has been confirmed."""
    return "The submission has been successfully unclaimed."


def get_cancel_blocks(submission: Submission, user: BlossomUser) -> List[Dict]:
    """Get the Slack message blocks for when the unclaiming has been cancelled."""
    text_block = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": get_cancel_text(),
        },
    }

    return [
        text_block,
        _get_submission_info_block(submission, user),
    ]


def get_cancel_text() -> str:
    """Get the text for when the unclaiming has been cancelled."""
    return "The unclaiming has been cancelled."


def _get_submission_info_block(submission: Submission, user: BlossomUser) -> Dict:
    """Get the info text for the submission to unclaim."""
    title_link = f"*<{submission.tor_url}|{submission.title}>*"
    source_link = f"<{submission.url}|{get_source(submission)}>"
    user_link = f"<https://reddit.com/u/{user.username}/?sort=new|u/{user.username}>"

    text = f"{title_link} on {source_link}\nClaimed by {user_link}"

    return {
        "type": "section",
        "text": {"type": "mrkdwn", "text": text},
    }


def _get_ask_confirmation_buttons_block(submission: Submission) -> Dict:
    """Get the action buttons for the confirmation of an unclaim request."""
    return {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "style": "primary",
                "text": {"type": "plain_text", "text": "Confirm"},
                "value": f"unclaim_confirm_{submission.id}",
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Cancel"},
                "value": f"unclaim_cancel_{submission.id}",
            },
        ],
    }
