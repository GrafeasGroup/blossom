from typing import Dict

from api.models import TranscriptionCheck
from authentication.models import BlossomUser


def _process_claim(check: TranscriptionCheck, mod: BlossomUser) -> None:
    """Process the claim of a transcription check."""
    if check.moderator is not None:
        # TODO: Send an error message in this case
        return

    check.moderator = mod
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

    if action == "claim":
        _process_claim(check, mod)

    # The mod pressing the button must be the same who claimed the check
    if check.moderator != mod:
        # TODO: Send an error message in this case
        return
