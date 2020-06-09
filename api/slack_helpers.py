import binascii
import hmac
import os
import threading
from typing import Any, Callable, Dict, List, Tuple, Union
from unittest import mock

import pytz
import slack
from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone
from slack.web.slack_response import SlackResponse

from api.models import Transcription
from api.serializers import VolunteerSerializer
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


def neat_printer(dictionary: Dict, titles: List, width: int) -> List:
    """
    Take a dict and make it into a tab-separated table.

    Adapted from
    https://github.com/varadchoudhari/Neat-Dictionary/blob/master
    /src/Python%203/neat-dictionary-fixed-column-width.py
    """
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


def get_days() -> Tuple[Union[int, float], Union[int, float]]:
    """Return the number of days since the day we opened."""
    # the autoformatter thinks this is evil if it's all on one line.
    # Breaking it up a little for my own sanity.
    start_date = pytz.timezone("UTC").localize(
        timezone.datetime(day=1, month=4, year=2017), is_dst=None
    )

    return divmod((timezone.now() - start_date).days, 365)


def send_help_message(event: Dict) -> None:
    """Post a help message to slack."""
    client.chat_postMessage(
        channel=event.get("channel"), text=i18n["slack"]["help_message"]
    )


def send_summary_message(event: Dict) -> None:
    """Post a summary message to slack."""
    client.chat_postMessage(
        channel=event.get("channel"),
        text=i18n["slack"]["summary_message"].format(
            BlossomUser.objects.filter(is_volunteer=True).count(),
            Transcription.objects.count(),
            get_days()[0],
            get_days()[1],
            "days" if get_days()[1] != 1 else "day",
        ),
    )


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

    msg = f"{emote} GitHub Sponsors: [{action}] - {username} | {sponsorlevel} {emote}"
    client.chat_postMessage(channel="org_running", text=msg)


def send_info(event: Dict, message: str) -> Union[SlackResponse, None]:
    """Send info about a user to slack."""
    parsed_message = message.split()
    if len(parsed_message) == 1:
        # they just sent an empty info message
        return send_summary_message(event)

    if len(parsed_message) == 2:
        if u := BlossomUser.objects.filter(username__iexact=parsed_message[1]).first():
            v_s = VolunteerSerializer(u, many=False).data
            return client.chat_postMessage(
                channel=event.get("channel"),
                text=i18n["slack"]["user_info"].format(
                    u.username,
                    "\n".join(
                        neat_printer(
                            v_s, ["Key", "Value"], len(max(v_s.keys(), key=len)) + 2
                        )
                    ),
                ),
            )
        else:
            return client.chat_postMessage(
                channel=event.get("channel"), text=i18n["slack"]["no_user_by_that_name"]
            )

    client.chat_postMessage(
        channel=event.get("channel"), text=i18n["slack"]["too_many_params"]
    )


def process_blacklist(event: Dict, message: str) -> SlackResponse:
    """Blacklist a user based on a message from slack."""
    parsed_message = message.split()
    if len(parsed_message) == 1:
        # they didn't give a username
        return client.chat_postMessage(
            channel=event.get("channel"),
            text=i18n["slack"]["blacklist"]["missing_username"],
        )
    elif len(parsed_message) == 2:
        if u := BlossomUser.objects.filter(username__iexact=parsed_message[1]).first():
            if u.blacklisted:
                u.blacklisted = False
                u.save()
                return client.chat_postMessage(
                    channel=event.get("channel"),
                    text=i18n["slack"]["blacklist"]["success_undo"].format(
                        parsed_message[1]
                    ),
                )
            else:
                u.blacklisted = True
                u.save()
                return client.chat_postMessage(
                    channel=event.get("channel"),
                    text=i18n["slack"]["blacklist"]["success"].format(
                        parsed_message[1]
                    ),
                )
        else:
            return client.chat_postMessage(
                channel=event.get("channel"),
                text=i18n["slack"]["blacklist"]["unknown_username"],
            )
    else:
        return client.chat_postMessage(
            channel=event.get("channel"), text=i18n["slack"]["too_many_params"]
        )


@fire_and_forget
def process_message(data: Dict) -> None:
    """Identify the purpose of a slack message and route accordingly."""
    e = data.get("event")  # noqa: VNE001

    try:
        # What comes in: "<@UTPFNCQS2> hello!"
        # Strip out the beginning section and see what's left.
        # Note: black and flake8 disagree on the formatting. Black wins.
        message = e["text"][e["text"].index(">") + 2 :].lower()  # noqa: E203
    except IndexError:
        client.chat_postMessage(
            channel=e.get("channel"),
            text="Sorry, something went wrong and I couldn't parse your message.",
        )
        return

    if not message:
        client.chat_postMessage(
            channel=e.get("channel"),
            text="Sorry, I wasn't able to get text out of that. Try again.",
        )

    elif "help" in message:
        send_help_message(e)

    elif "summary" in message:
        send_summary_message(e)

    elif "info" in message:
        send_info(e, message)

    elif "blacklist" in message:
        process_blacklist(e, message)

    else:
        client.chat_postMessage(
            channel=e.get("channel"), text="Sorry, I'm not sure what you're asking for."
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
