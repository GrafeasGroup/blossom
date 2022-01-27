import logging
from typing import Dict, List

import requests

from api.helpers import fire_and_forget
from api.serializers import VolunteerSerializer
from api.slack import client
from api.slack.events import process_submission_report_update
from api.slack.utils import clean_links, dict_to_table, get_message
from api.views.misc import Summary
from authentication.models import BlossomUser
from blossom.strings import translation

logger = logging.getLogger("api.slack.commands")

i18n = translation()


@fire_and_forget
def process_message(data: Dict) -> None:
    """Identify the purpose of a slack message and route accordingly."""
    if data.get("type") == "block_actions":
        value = data["actions"][0].get("value")
        if "keep" in value or "remove" in value:
            process_submission_report_update(data)
        else:
            client.chat_postMessage(
                channel=data["channel"]["id"],
                text=i18n["slack"]["errors"]["unknown_payload"].format(value),
            )
        return

    e = data.get("event")  # noqa: VNE001
    channel = e.get("channel")

    message = get_message(data)
    actions = data.get("actions")

    if not message and not actions:
        client.chat_postMessage(
            channel=channel, text=i18n["slack"]["errors"]["message_parse_error"],
        )
        return

    if not message:
        client.chat_postMessage(
            channel=channel, text=i18n["slack"]["errors"]["empty_message_error"],
        )
        return

    # format: first word command -> function to call
    # Reformatted this way because E228 hates the if / elif routing tree.
    options = {
        "ping": pong_cmd,
        "help": help_cmd,
        "reset": reset_cmd,
        "info": info_cmd,
        "blacklist": blacklist_cmd,
        "watch": watch_cmd,
        "unwatch": unwatch_cmd,
        "watchlist": watchlist_cmd,
        "dadjoke": dadjoke_cmd,
    }

    for key in options.keys():
        if message.startswith(key):
            options[key](channel, message)
            return

    # if we fall through here, we got a message that we don't understand.
    client.chat_postMessage(
        channel=channel, text=i18n["slack"]["errors"]["unknown_request"]
    )


def help_cmd(channel: str) -> None:
    """Post a help message to slack."""
    client.chat_postMessage(channel=channel, text=i18n["slack"]["help_message"])


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
        if user := BlossomUser.objects.filter(
            username__iexact=parsed_message[1]
        ).first():
            v_data = VolunteerSerializer(user).data
            msg = i18n["slack"]["user_info"].format(
                user.username, "\n".join(dict_to_table(v_data))
            )
        else:
            msg = i18n["slack"]["errors"]["no_user_by_that_name"]
    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)


def pong_cmd(channel: str) -> None:
    """Respond to pings."""
    client.chat_postMessage(channel=channel, text="PONG")


def reset_cmd(channel: str, message: str) -> None:
    """Reset the CoC status for a given volunteer."""
    parsed_message = message.split()
    if len(parsed_message) == 1:
        # they didn't give a username
        msg = i18n["slack"]["errors"]["missing_username"]
    elif len(parsed_message) == 2:
        username = clean_links(parsed_message[1])
        if user := BlossomUser.objects.filter(username__iexact=username).first():
            if user.accepted_coc:
                user.accepted_coc = False
                user.save()
                msg = i18n["slack"]["reset_coc"]["success"].format(username)
            else:
                user.accepted_coc = True
                user.save()
                msg = i18n["slack"]["reset_coc"]["success_undo"].format(username)
        else:
            msg = i18n["slack"]["errors"]["unknown_username"]

    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)


def watch_cmd(channel: str, message: str) -> None:
    """Overwrite the transcription check percentage of a user."""
    parsed_message = message.split()

    if len(parsed_message) == 1:
        # they didn't give a username
        msg = i18n["slack"]["errors"]["missing_username"]
    elif len(parsed_message) <= 3:
        username = clean_links(parsed_message[1])
        if user := BlossomUser.objects.filter(username__iexact=username).first():
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

            # Overwrite the check percentage
            user.overwrite_check_percentage = decimal_percentage
            user.save()

            msg = i18n["slack"]["watch"]["success"].format(
                user=user.username, percentage=decimal_percentage
            )
        else:
            msg = i18n["slack"]["errors"]["unknown_username"]

    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)


def unwatch_cmd(channel: str, message: str) -> None:
    """Set the transcription checks back to automatic."""
    parsed_message = message.split()

    if len(parsed_message) == 1:
        # they didn't give a username
        msg = i18n["slack"]["errors"]["missing_username"]
    elif len(parsed_message) == 2:
        username = clean_links(parsed_message[1])
        if user := BlossomUser.objects.filter(username__iexact=username).first():
            # Set the check percentage back to automatic
            user.overwrite_check_percentage = None
            user.save()

            msg = i18n["slack"]["unwatch"]["success"].format(user=user.username)
        else:
            msg = i18n["slack"]["errors"]["unknown_username"]

    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)


def watchlist_cmd(channel: str, message: str) -> None:
    """Send a list of users who are currently being watched."""
    parsed_message = message.split()
    sorting = parsed_message[1] if len(parsed_message) > 1 else "percentage"

    response_msg = "**List of all watched users:**\n\n"

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
                response_msg += "*{}*: u/{}".format(
                    f"{usr.overwrite_check_percentage:.0%}".rjust(4, ""), usr.username
                )
                last_percentage = usr.overwrite_check_percentage
    elif sorting == "alphabetical":
        # Sort the users alphabetically
        watched_users.sort(key=lambda u: u.username.casefold(), reverse=True)

        for usr in watched_users:
            response_msg += "u/{} ({:.0%})".format(
                usr.username, usr.overwrite_check_percentage
            )
    else:
        response_msg = (
            f"Invalid sorting '{sorting}'. "
            "Use either 'percentage' or 'alphabetical'."
        )

    response_msg += "```"
    client.chat_postMessage(channel=channel, text=response_msg)


def dadjoke_cmd(channel: str, message: str, use_api: bool = True) -> None:
    """Send the pinged user a dad joke. Or just send everybody a joke."""
    parsed_message = message.split()
    ping_username, msg = None, None
    try:
        if use_api:
            joke = requests.get(
                "https://icanhazdadjoke.com/", headers={"Accept": "text/plain"}
            ).content.decode()
        else:
            raise Exception("Testing mode -- just use fallback.")
    except:  # noqa: E722
        joke = i18n["slack"]["dadjoke"]["fallback_joke"]

    if len(parsed_message) == 2:
        if parsed_message[1].startswith("<"):
            ping_username = parsed_message[1].upper()

        if ping_username:
            msg = i18n["slack"]["dadjoke"]["message"].format(ping_username, joke)

    if not msg:
        msg = joke

    client.chat_postMessage(channel=channel, text=msg, link_names=True)


def blacklist_cmd(channel: str, message: str) -> None:
    """Blacklist a user based on a message from slack."""
    parsed_message = message.split()
    if len(parsed_message) == 1:
        # they didn't give a username
        msg = i18n["slack"]["errors"]["missing_username"]
    elif len(parsed_message) == 2:
        username = clean_links(parsed_message[1])
        if user := BlossomUser.objects.filter(username__iexact=username).first():
            if user.blacklisted:
                user.blacklisted = False
                user.save()
                msg = i18n["slack"]["blacklist"]["success_undo"].format(username)
            else:
                user.blacklisted = True
                user.save()
                msg = i18n["slack"]["blacklist"]["success"].format(username)
        else:
            msg = i18n["slack"]["errors"]["unknown_username"]
    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)
