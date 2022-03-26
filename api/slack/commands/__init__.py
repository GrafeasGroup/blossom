"""The Slack commands for Blossom.

Every command must be registered in the __init__.py file.
"""
from typing import Dict

from api.slack import client
from api.slack.commands.blacklist import blacklist_cmd
from api.slack.commands.check import check_cmd
from api.slack.commands.dadjoke import dadjoke_cmd
from api.slack.commands.help import help_cmd
from api.slack.commands.info import info_cmd
from api.slack.commands.ping import ping_cmd
from api.slack.commands.reset import reset_cmd
from api.slack.commands.unwatch import unwatch_cmd
from api.slack.commands.warnings import warnings_cmd
from api.slack.commands.watch import watch_cmd
from api.slack.commands.watchlist import watchlist_cmd
from api.slack.commands.watchstatus import watchstatus_cmd
from api.slack.utils import get_message
from blossom.strings import translation

i18n = translation()


def process_command(data: Dict) -> None:
    """Process a Slack command.

    All commands need to be registered in this function.
    """
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
        "blacklist": blacklist_cmd,
        "check": check_cmd,
        "dadjoke": dadjoke_cmd,
        "help": help_cmd,
        "info": info_cmd,
        "ping": ping_cmd,
        "reset": reset_cmd,
        "unwatch": unwatch_cmd,
        "warnings": warnings_cmd,
        "watch": watch_cmd,
        "watchlist": watchlist_cmd,
        "watchstatus": watchstatus_cmd,
    }

    tokens = message.split()

    if len(tokens) > 0:
        # Find the command corresponding to the message
        cmd_name = tokens[0].casefold()
        for key in options.keys():
            if cmd_name == key:
                options[key](channel, message)
                return

    # if we fall through here, we got a message that we don't understand.
    client.chat_postMessage(
        channel=channel, text=i18n["slack"]["errors"]["unknown_request"]
    )
