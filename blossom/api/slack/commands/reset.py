from blossom.api.slack import client
from blossom.api.slack.utils import parse_user
from blossom.strings import translation

i18n = translation()


def reset_cmd(channel: str, message: str) -> None:
    """Reset the CoC status for a given volunteer."""
    parsed_message = message.split()
    if len(parsed_message) == 1:
        # they didn't give a username
        msg = i18n["slack"]["errors"]["missing_username"]
    elif len(parsed_message) == 2:
        user, username = parse_user(parsed_message[1])
        if user:
            if user.accepted_coc:
                user.accepted_coc = False
                user.save()
                msg = i18n["slack"]["reset_coc"]["success"].format(username)
            else:
                user.accepted_coc = True
                user.save()
                msg = i18n["slack"]["reset_coc"]["success_undo"].format(username)
        else:
            msg = i18n["slack"]["errors"]["unknown_username"].format(username=username)

    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)
