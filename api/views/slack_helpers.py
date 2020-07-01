import binascii
import hmac
import os
import threading
from typing import Any, Callable, Dict, List, Tuple
from unittest import mock

import slack
from django.conf import settings
from django.http import HttpRequest

from api.serializers import VolunteerSerializer
from api.views.misc import Summary
from authentication.models import BlossomUser
from blossom.strings import translation

if settings.ENABLE_SLACK is True:
    client = slack.WebClient(token=os.environ["SLACK_API_KEY"])
else:
    # this is to explicitly disable posting to Slack when doing local dev
    client = mock.Mock()

i18n = translation()


def fire_and_forget(
    func: Callable[[Any], Any], *args: Tuple, **kwargs: Dict
) -> Callable[[Any], Any]:
    """
    Decorate functions to build a thread for a given function and trigger it.

    Originally from https://stackoverflow.com/a/59043636, this function
    prepares a thread for a given function and then starts it, intentionally
    severing communication with the thread so that we can continue moving
    on.

    This should be used sparingly and only when we are 100% sure that
    the function we are passing does not need to communicate with the main
    process and that it will exit cleanly (and that if it explodes, we don't
    care).
    """

    def wrapped(*args: Tuple, **kwargs: Dict) -> None:
        threading.Thread(target=func, args=(args), kwargs=kwargs).start()

    return wrapped


def dict_to_table(dictionary: Dict, titles: List = None, width: int = None) -> List:
    """
    Take a dictionary and make it into a tab-separated table.

    Adapted from
    https://github.com/varadchoudhari/Neat-Dictionary/blob/master
    /src/Python%203/neat-dictionary-fixed-column-width.py
    """
    if not titles:
        titles = ["Key", "Value"]
    if not width:
        width = len(max(dictionary.keys(), key=len)) + 2

    return_list = []
    formatting = ""
    for i in range(0, len(titles)):
        formatting += "{:<" + str(width) + "}"
        formatting += " | "
    # trim off that last separator
    formatting = formatting[:-3]
    return_list.append(formatting.format(*titles))
    return_list.append(f"{'-' * width * len(titles)}")
    for key, value in dictionary.items():
        sv = []
        if isinstance(value, list):
            for subvalue in value:
                sv.append(str(subvalue))
        else:
            if value is None:
                value = "None"
            sv = [str(value)]
        return_list.append(formatting.format(key, ", ".join(sv)))
    return return_list


def send_help_message(channel: str) -> None:
    """Post a help message to slack."""
    client.chat_postMessage(channel=channel, text=i18n["slack"]["help_message"])


def send_summary_message(channel: str) -> None:
    """Post a summary message to slack."""
    data = Summary().generate_summary()
    client.chat_postMessage(channel=channel, text=dict_to_table(data))


def send_github_sponsors_message(data: Dict, action: str) -> None:
    """
    Process the POST request from GitHub Sponsors.

    Every time someone performs an action on GitHub Sponsors, we'll get
    a POST request with the intent and some other information. This translates
    the GitHub call to something that Slack can understand, then forwards it
    to the #org_running channel.
    """
    emote = ":tada:"
    if action == "cancelled" or action == "pending_cancellation":
        emote = ":sob:"
    if (
        action == "edited"
        or action == "tier_changed"
        or action == "pending_tier_change"
    ):
        emote = ":rotating_light:"
    username = data["sponsorship"]["sponsor"]["login"]
    sponsorlevel = data["sponsorship"]["tier"]["name"]

    msg = i18n["slack"]["github_sponsor_update"].format(
        emote, action, username, sponsorlevel
    )
    client.chat_postMessage(channel="org_running", text=msg)


def send_info(event: Dict, message: str) -> None:
    """Send info about a user to slack."""
    parsed_message = message.split()
    msg = None
    if len(parsed_message) == 1:
        # they just sent an empty info message
        data = Summary().generate_summary()
        msg = dict_to_table(data)

    if len(parsed_message) == 2:
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

    client.chat_postMessage(channel=event.get("channel"), text=msg)


def process_blacklist(event: Dict, message: str) -> None:
    """Blacklist a user based on a message from slack."""
    parsed_message = message.split()
    if len(parsed_message) == 1:
        # they didn't give a username
        msg = i18n["slack"]["blacklist"]["missing_username"]
    elif len(parsed_message) == 2:
        if user := BlossomUser.objects.filter(
            username__iexact=parsed_message[1]
        ).first():
            if user.blacklisted:
                user.blacklisted = False
                user.save()
                msg = i18n["slack"]["blacklist"]["success_undo"].format(
                    parsed_message[1]
                )
            else:
                user.blacklisted = True
                user.save()
                msg = i18n["slack"]["blacklist"]["success"].format(parsed_message[1])
        else:
            msg = i18n["slack"]["blacklist"]["unknown_username"]
    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=event.get("channel"), text=msg)


def get_message(data: Dict) -> str:
    """
    Pull message text out of slack event.

    What comes in: "<@UTPFNCQS2> hello!" Strip out the beginning section
    and see what's left.
    """
    event = data.get("event")
    # Note: black and flake8 disagree on the formatting. Black wins.
    return event["text"][event["text"].index(">") + 2 :].lower()  # noqa: E203


@fire_and_forget
def process_message(data: Dict) -> None:
    """Identify the purpose of a slack message and route accordingly."""
    e = data.get("event")  # noqa: VNE001
    channel = e.get("channel")

    try:
        message = get_message(data)
    except IndexError:
        client.chat_postMessage(
            channel=channel, text=i18n["slack"]["errors"]["message_parse_error"],
        )
        return

    if not message:
        client.chat_postMessage(
            channel=channel, text=i18n["slack"]["errors"]["empty_message_error"],
        )

    elif "help" in message:
        send_help_message(channel)

    elif "summary" in message:
        send_summary_message(channel)

    elif "info" in message:
        send_info(e, message)

    elif "blacklist" in message:
        process_blacklist(e, message)

    else:
        client.chat_postMessage(
            channel=channel, text=i18n["slack"]["errors"]["unknown_request"]
        )


def is_valid_github_request(request: HttpRequest) -> bool:
    """Verify that a webhook from github sponsors is encoded using our key."""
    if (github_signature := request.headers.get("x-hub-signature")) is None:
        return False

    body_hex = binascii.hexlify(
        hmac.digest(
            msg=request.body,
            key=settings.GITHUB_SPONSORS_SECRET_KEY.encode(),
            digest="sha1",
        )
    ).decode()

    body_hex = f"sha1={body_hex}"
    return hmac.compare_digest(body_hex, github_signature)
