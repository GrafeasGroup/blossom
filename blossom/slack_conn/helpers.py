import os
import threading
from typing import Dict
from unittest import mock
import binascii
import hmac

import pytz
import slack
from django.conf import settings
from django.utils import timezone

from api.models import Transcription
from authentication.models import BlossomUser
from api.serializers import VolunteerSerializer
from blossom.strings import translation

if settings.ENABLE_SLACK == True:
    client = slack.WebClient(token=os.environ["SLACK_API_KEY"])
else:
    client = mock.Mock()

i18n = translation()


# https://stackoverflow.com/a/59043636
def fire_and_forget(f, *args, **kwargs):
    def wrapped(*args, **kwargs):
        threading.Thread(target=f, args=(args), kwargs=kwargs).start()

    return wrapped


# adapted from
# https://github.com/varadchoudhari/Neat-Dictionary/blob/master
# /src/Python%203/neat-dictionary-fixed-column-width.py
def neat_printer(dictionary, titles, width):
    return_dict = []
    formatting = ""
    for i in range(0, len(titles)):
        formatting += "{:<" + str(width) + "}"
        formatting += " | "
    # trim off that last separator
    formatting = formatting[:-3]
    return_dict.append(formatting.format(*titles))
    return_dict.append(f"{'-' * width * len(titles)}")
    for key, value in dictionary.items():
        sv = []
        if isinstance(value, list):
            for subvalue in value:
                sv.append(str(subvalue))
        else:
            if value is None:
                value = "None"
            sv = [str(value)]
        return_dict.append(formatting.format(key, *sv))
    return return_dict


def get_days():
    # the autoformatter thinks this is evil if it's all on one line.
    # Breaking it up a little for my own sanity.
    start_date = pytz.timezone("UTC").localize(
        timezone.datetime(day=1, month=4, year=2017), is_dst=None
    )

    return divmod((timezone.now() - start_date).days, 365)


def send_help_message(event):
    client.chat_postMessage(
        channel=event.get("channel"), text=i18n["slack"]["help_message"]
    )


def send_summary_message(event):
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
    username = data['sponsorship']['sponsor']['login']
    sponsorlevel = data['sponsorship']['tier']['name']

    msg = f"{emote} GitHub Sponsors: [{action}] - {username} | {sponsorlevel} {emote}"
    client.chat_postMessage(channel="org_running", text=msg)


def send_info(event, message):
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


def process_blacklist(event, message):
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
    e = data.get("event")

    try:
        # What comes in: "<@UTPFNCQS2> hello!"
        # Strip out the beginning section and see what's left.
        message = e["text"][e["text"].index(">") + 2 :].lower()
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


def is_valid_github_request(request):
    if (github_signature := request.headers["x-hub-signature"]) is None:
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
