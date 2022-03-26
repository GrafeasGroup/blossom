from api.serializers import VolunteerSerializer
from api.slack import client
from api.slack.utils import dict_to_table, parse_user
from api.views.misc import Summary
from blossom.strings import translation

i18n = translation()


def info_cmd(channel: str, message: str) -> None:
    """Send info about a user to slack."""
    parsed_message = message.split()
    if len(parsed_message) == 1:
        # they just sent an empty info message, create a summary response
        data = Summary().generate_summary()
        client.chat_postMessage(
            channel=channel,
            text=i18n["slack"]["server_summary"].format("\n".join(dict_to_table(data))),
        )
        return

    elif len(parsed_message) == 2:
        user, username = parse_user(parsed_message[1])
        if user:
            v_data = VolunteerSerializer(user).data
            msg = i18n["slack"]["user_info"].format(
                username, "\n".join(dict_to_table(v_data))
            )
        else:
            msg = i18n["slack"]["errors"]["unknown_username"].format(username=username)
    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)
