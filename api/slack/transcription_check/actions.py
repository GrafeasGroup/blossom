from typing import Dict

from django.utils import timezone

from api.models import TranscriptionCheck
from authentication.models import BlossomUser


def _update_db_model(check: TranscriptionCheck, mod: BlossomUser, action: str) -> None:
    """Update the DB model according to the action taken."""
    check_status = TranscriptionCheck.TranscriptionCheckStatus

    if action == "claim":
        check.moderator = mod
        check.claim_time = timezone.now
    if action == "unclaim":
        check.moderator = None
        check.claim_time = None
    elif action == "pending":
        check.status = check_status.PENDING
        check.complete_time = None
    if action == "approved":
        check.status = check_status.APPROVED
        check.complete_time = timezone.now
    elif action == "comment-pending":
        check.status = check_status.COMMENT_PENDING
        check.complete_time = None
    elif action == "comment-resolved":
        check.status = check_status.COMMENT_RESOLVED
        check.complete_time = timezone.now
    elif action == "warning-pending":
        check.status = check_status.WARNING_PENDING
        check.complete_time = None
    elif action == "warning-resolved":
        check.status = check_status.WARNING_RESOLVED
        check.complete_time = timezone.now
    else:
        # TODO: Send error message
        return

    # Save the changes to the DB
    check.save()


def process_check_action(data: Dict) -> None:
    """Process an action related to transcription checks."""
    value = data["actions"][0].get("value")
    parts = value.split("_")
    action = parts[1]
    check_id = parts[2]

    # Retrieve the corresponding objects form the DB
    check = TranscriptionCheck.objects.filter(id=check_id).first()
    mod = BlossomUser.objects.filter(username=data["user"]["username"]).first()

    # TODO: Send an error message in these cases
    if check is None:
        return
    if mod is None:
        return

    # Only unclaimed checks can be claimed
    if action == "claim" and check.moderator is not None:
        # TODO: Send an error message
        return
    # A claimed check can only be worked on by the mod who claimed it
    if action != "claim" and check.moderator != mod:
        # TODO: Send an error message in this case
        return

    _update_db_model(check, mod, action)

    # TODO: Update Slack message
