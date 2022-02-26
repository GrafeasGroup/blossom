import logging
from typing import Dict

from django.utils import timezone

from api.models import TranscriptionCheck
from api.slack.transcription_check.messages import (
    reply_to_action_with_ping,
    update_check_message,
)
from authentication.models import BlossomUser

logger = logging.getLogger("api.slack.transcription_check.actions")


def _update_db_model(check: TranscriptionCheck, mod: BlossomUser, action: str) -> bool:
    """Update the DB model according to the action taken.

    :returns: False, if the action is unknown, else True
    """
    check_status = TranscriptionCheck.TranscriptionCheckStatus

    if action == "claim":
        check.moderator = mod
        check.claim_time = timezone.now()
    elif action == "unclaim":
        check.moderator = None
        check.claim_time = None
    elif action == "pending":
        check.status = check_status.PENDING
        check.complete_time = None
    elif action == "approved":
        check.status = check_status.APPROVED
        check.complete_time = timezone.now()
    elif action == "comment-pending":
        check.status = check_status.COMMENT_PENDING
        check.complete_time = None
    elif action == "comment-resolved":
        check.status = check_status.COMMENT_RESOLVED
        check.complete_time = timezone.now()
    elif action == "warning-pending":
        check.status = check_status.WARNING_PENDING
        check.complete_time = None
    elif action == "warning-resolved":
        check.status = check_status.WARNING_RESOLVED
        check.complete_time = timezone.now()
    else:
        # Unknown action
        return False

    # Save the changes to the DB
    check.save()
    return True


def process_check_action(data: Dict) -> None:
    """Process an action related to transcription checks."""
    value = data["actions"][0].get("value")
    parts = value.split("_")
    action = parts[1]
    check_id = parts[2]
    mod_username = data["user"]["name"]

    # Retrieve the corresponding objects form the DB
    check = TranscriptionCheck.objects.filter(id=check_id).first()
    mod = BlossomUser.objects.filter(username=mod_username).first()

    if check is None:
        logger.warning(f"I couldn't find a check with ID {check_id}!")
        reply_to_action_with_ping(data, f"I couldn't find a check with ID {check_id}!")
        return
    if mod is None:
        logging.warning(
            f"I couldn't find a mod with username u/{mod_username}.\n"
            "Did you set your username on Slack?",
        )
        reply_to_action_with_ping(
            data,
            f"I couldn't find a mod with username u/{mod_username}.\n"
            "Did you set your username on Slack?",
        )
        return

    # Only unclaimed checks can be claimed
    if action == "claim" and check.moderator is not None:
        logger.warning(f"Check {check_id} is already claimed by someone!")
        reply_to_action_with_ping(
            data, f"Check {check_id} is already claimed by someone!"
        )
        return
    # If it's not a claim it must already be claimed by someone
    if action != "claim" and check.moderator is None:
        logger.warning(f"Check {check_id} is not claimed by anyone yet!")
        reply_to_action_with_ping(
            data, f"Check {check_id} is not claimed by anyone yet!"
        )
    # A claimed check can only be worked on by the mod who claimed it
    if action != "claim" and check.moderator != mod:
        logger.warning(
            f"Check {check_id} is claimed by u/{check.moderator.username}, not by you!",
        )
        reply_to_action_with_ping(
            data,
            f"Check {check_id} is claimed by u/{check.moderator.username}, not by you!",
        )
        return

    # Try to update the DB model based on the action
    if not _update_db_model(check, mod, action):
        # Unknown action type
        logger.warning(f"Action '{action}' is invalid for check {check_id}!",)
        reply_to_action_with_ping(
            data, f"Action '{action}' is invalid for check {check_id}!",
        )

    update_check_message(check)
