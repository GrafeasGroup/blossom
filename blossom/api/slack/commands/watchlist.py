from typing import List

from blossom.api.slack import client
from blossom.authentication.models import BlossomUser
from blossom.strings import translation

i18n = translation()


def watchlist_cmd(channel: str, message: str) -> None:
    """Send a list of users who are currently being watched."""
    parsed_message = message.split()
    sorting = parsed_message[1] if len(parsed_message) > 1 else "percentage"

    response_msg = "*List of all watched users:*\n\n"

    watched_users: List[BlossomUser] = list(
        BlossomUser.objects.filter(overwrite_check_percentage__isnull=False)
    )

    if len(watched_users) == 0:
        # No users are watched yet
        response_msg += (
            "None yet. Use `@Blossom watch <username> <percentage>` to watch a user."
        )

        client.chat_postMessage(channel=channel, text=response_msg)
        return
    else:
        response_msg += "```\n"

    if sorting == "percentage":
        # Group the users by percentages
        watched_users.sort(key=lambda u: u.overwrite_check_percentage, reverse=True)
        last_percentage = None

        for usr in watched_users:
            if usr.overwrite_check_percentage == last_percentage:
                response_msg += " " * 6 + f"u/{usr.username}\n"
            else:
                response_msg += "{}: u/{}\n".format(
                    f"{usr.overwrite_check_percentage:.0%}".rjust(4, " "), usr.username
                )
                last_percentage = usr.overwrite_check_percentage
    elif sorting == "alphabetical":
        # Sort the users alphabetically
        watched_users.sort(key=lambda u: u.username.casefold())

        for usr in watched_users:
            response_msg += "u/{} ({:.0%})\n".format(
                usr.username, usr.overwrite_check_percentage
            )
    else:
        # Invalid sorting
        response_msg = (
            f"Invalid sorting '{sorting}'. "
            "Use either 'percentage' or 'alphabetical'."
        )
        client.chat_postMessage(channel=channel, text=response_msg)
        return

    response_msg += "```"
    client.chat_postMessage(channel=channel, text=response_msg.strip())
