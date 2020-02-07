import json
import logging
import os
from pprint import pprint as pp

import slack
from django.http import HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from typing import Dict
from django.utils import timezone
import pytz

from blossom.slack_conn.helpers import fire_and_forget
from blossom.authentication.models import BlossomUser
from blossom.api.models import Transcription

client = slack.WebClient(token=os.environ['SLACK_API_KEY'])

help_message = """
Help is on the way!\n\n
Get information about a user: `@blossom info {username}`\n
Get general server information: `@blossom info` | `@blossom summary`\n
Render this message: `@blossom help`
"""


def get_days():
    # the autoformatter thinks this is evil if it's all on one line.
    # Breaking it up a little for my own sanity.
    start_date = pytz.timezone("UTC").localize(
        timezone.datetime(day=1, month=4, year=2017), is_dst=None
    )

    return divmod((timezone.now() - start_date).days, 365)


summary_message = """
Volunteer count: {0}\n
Transcription count: {1}\n

How long we've been doing this: {2} years, {3} {4}!
""".format(
    BlossomUser.objects.filter(is_volunteer=True).count(),
    Transcription.objects.count(),
    get_days()[0],
    get_days()[1],
    "days" if get_days()[1] != 1 else "day"
)


@fire_and_forget
def process_message(data: Dict) -> None:
    event = data.get('event')

    try:
        # What comes in: "<@UTPFNCQS2> hello!"
        # Strip out the beginning section and see what's left.
        message = event['text'][event['text'].index('>') + 2:].lower()
    except IndexError:
        client.chat_postMessage(
            channel=event.get('channel'),
            text="Sorry, something went wrong and I couldn't parse your message."
        )
        return

    if not message:
        client.chat_postMessage(
            channel=event.get('channel'),
            text="Sorry, I wasn't able to get text out of that. Try again."
        )

    elif "help" in message:
        client.chat_postMessage(
            channel=event.get('channel'),
            text=f"{help_message}"
        )
    elif "summary" in message:
        client.chat_postMessage(
            channel=event.get('channel'),
            text=f"{summary_message}"
        )


@csrf_exempt
def slack_endpoint(request: HttpRequest) -> HttpResponse:
    """
    Slack plays a lot of games with its API and honestly it's one of the
    most frustrating things I've ever worked with. There are a couple of
    things that we'll need to do in this view:

    * No matter what, respond within three seconds _of slack sending the
      ping_ -- we really have less than three seconds. Slack is impatient.
      Slack cares not for your feelings.
    * Sometimes we'll get a challenge that we have to respond to, but it's
      unclear if we'll only get it during setup or whenever Slack feels
      like it.

    So how do we get around Slack's ridiculous timeouts?

    ⋆ . ˚ * ✧ T H R E A D I N G ✧ * ˚ . ⋆
    -------------------------------------

    We extract the information we need out of the request, pass it off
    to a different function to actually figure out what the hell Slack
    wants, and then send our own response. In the meantime, we basically
    just send a 200 OK as fast as we can so that Slack doesn't screw up
    our day.

    :param request: HttpRequest
    :return: JsonResponse, HttpRequest
    """
    json_data = json.loads(request.body)
    if json_data.get('challenge'):
        # looks like we got hit with the magic handshake packet. Send it
        # back to its maker.
        return HttpResponse(json_data['challenge'])
    # It's not a challenge, so just hand off data processing to the
    # thread and give Slack the result it craves.
    process_message(json_data)
    return HttpResponse(status=200)
