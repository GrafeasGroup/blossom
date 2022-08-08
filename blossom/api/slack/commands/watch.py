from blossom.api.slack import client
from blossom.api.slack.utils import parse_user
from blossom.strings import translation

i18n = translation()


def watch_cmd(channel: str, message: str) -> None:
    """Overwrite the transcription check percentage of a user."""
    parsed_message = message.split()

    if len(parsed_message) == 1:
        # they didn't give a username
        msg = i18n["slack"]["errors"]["missing_username"]
    elif len(parsed_message) <= 3:
        user, username = parse_user(parsed_message[1])
        if user:
            if len(parsed_message) == 2:
                # they didn't give a percentage, default to 100%
                decimal_percentage = 1
            else:
                # parse the provided percentage
                percentage = parsed_message[2]

                try:
                    # Try to parse the new check percentage
                    percentage = int(percentage.rstrip(" %"))
                    if percentage < 0 or percentage > 100:
                        raise ValueError

                    decimal_percentage = percentage / 100
                except ValueError:
                    # The percentage is invalid
                    msg = i18n["slack"]["watch"]["invalid_percentage"].format(
                        percentage=percentage
                    )
                    client.chat_postMessage(channel=channel, text=msg)
                    return

            # Only allow to set the percentage if it's higher than the default
            if decimal_percentage < user.auto_check_percentage:
                msg = i18n["slack"]["watch"]["percentage_too_low"].format(
                    auto_percentage=user.auto_check_percentage
                )
            else:
                # Remember the percentage before the overwrite
                previous = user.transcription_check_reason(ignore_low_activity=True)
                # Overwrite the check percentage
                user.overwrite_check_percentage = decimal_percentage
                user.save()

                msg = i18n["slack"]["watch"]["success"].format(
                    user=username, percentage=decimal_percentage, previous=previous
                )
        else:
            msg = i18n["slack"]["errors"]["unknown_username"].format(username=username)

    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)
