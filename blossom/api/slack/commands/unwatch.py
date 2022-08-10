from blossom.api.slack import client
from blossom.api.slack.utils import parse_user
from blossom.strings import translation

i18n = translation()


def unwatch_cmd(channel: str, message: str) -> None:
    """Set the transcription checks back to automatic."""
    parsed_message = message.split()

    if len(parsed_message) == 1:
        # they didn't give a username
        msg = i18n["slack"]["errors"]["missing_username"]
    elif len(parsed_message) == 2:
        user, username = parse_user(parsed_message[1])
        if user:
            # Set the check percentage back to automatic
            user.overwrite_check_percentage = None
            user.save()

            msg = i18n["slack"]["unwatch"]["success"].format(user=username)
        else:
            msg = i18n["slack"]["errors"]["unknown_username"].format(username=username)

    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)
