import logging
import os
from typing import Dict

import praw.reddit
import prawcore.exceptions

from blossom.api.models import Submission
from blossom.api.slack import client
from blossom.api.slack.messages.unclaim import (
    get_already_completed_blocks,
    get_already_unclaimed_blocks,
    get_cancel_blocks,
    get_cancel_text,
    get_confirm_blocks,
    get_confirm_text,
)
from blossom.authentication.models import BlossomUser
from blossom.reddit import REDDIT
from blossom.strings import translation

i18n = translation()

logger = logging.getLogger("blossom.api.actions.unclaim")

UNCLAIM_REDDIT_FLAIR_ID = os.getenv("UNCLAIM_REDDIT_FLAIR_ID")


def process_unclaim_action(data: Dict) -> None:
    """Handle a mod clicking a button on an unclaim confirmation message."""
    value = data["actions"][0].get("value")
    parts = value.split("_")

    channel_id = data["channel"]["id"]
    message_ts = data["message"]["ts"]

    action_type = parts[1]
    submission_id = parts[2]
    user_id = parts[3]

    submission = Submission.objects.get(id=submission_id)
    user = BlossomUser.objects.get(id=user_id)

    if action_type == "confirm":
        _process_unclaim_confirm(channel_id, message_ts, submission, user)
    elif action_type == "cancel":
        _process_unclaim_cancel(channel_id, message_ts, submission, user)
    else:
        # Invalid action type
        client.chat_postMessage(
            channel=channel_id,
            text=i18n["slack"]["unclaim"]["invalid_action"].format(action=action_type),
        )


def _process_unclaim_confirm(
    channel_id: str, message_ts: str, submission: Submission, user: BlossomUser
) -> None:
    """Handle a mod confirming the unclaim action."""
    tor_url = submission.tor_url

    if submission.claimed_by is None:
        # Nobody claimed this submission, abort
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            blocks=get_already_unclaimed_blocks(submission, user),
            text=i18n["slack"]["unclaim"]["not_claimed"].format(tor_url=tor_url),
        )
        return

    author = submission.claimed_by

    if submission.completed_by is not None:
        # The submission is already completed, abort
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            blocks=get_already_completed_blocks(submission, user),
            text=i18n["slack"]["unclaim"]["already_completed"].format(
                tor_url=submission.tor_url, username=user.username
            ),
        )
        return

    # Actually unclaim the submission
    submission.claimed_by = None
    submission.claim_time = None
    submission.save()

    # Notify the mods
    response = client.chat_update(
        channel=channel_id,
        ts=message_ts,
        blocks=get_confirm_blocks(submission, user),
        text=get_confirm_text(),
    )
    if not response["ok"]:
        logger.error(f"Could not update unclaim for submission {submission.id} on Slack!")

    # Update the Reddit flair
    _unclaim_reddit_flair(submission)


def _process_unclaim_cancel(
    channel_id: str, message_ts: str, submission: Submission, user: BlossomUser
) -> None:
    """Handle a mod cancelling the unclaim action."""
    # Notify the mods
    response = client.chat_update(
        channel=channel_id,
        ts=message_ts,
        blocks=get_cancel_blocks(submission, user),
        text=get_cancel_text(),
    )
    if not response["ok"]:
        logger.error(f"Could not update unclaim for submission {submission.id} on Slack!")


def _unclaim_reddit_flair(submission: Submission) -> None:
    """Update the Reddit flair of the submission to indicate that it's unclaimed."""
    if UNCLAIM_REDDIT_FLAIR_ID is None:
        logger.error("The env variable UNCLAIM_REDDIT_FLAIR_ID is not defined!")
        return

    try:
        reddit_id = praw.reddit.Submission.id_from_url(submission.tor_url)
        REDDIT.submission(reddit_id).flair.select(flair_template_id=UNCLAIM_REDDIT_FLAIR_ID)
    except prawcore.ResponseException:
        logger.exception("Failed to change flair to unclaimed on Reddit")
