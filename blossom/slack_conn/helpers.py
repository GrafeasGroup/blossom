import os
import threading
from typing import Dict

import pytz
import slack
from django.utils import timezone

from blossom.api.models import Transcription
from blossom.authentication.models import BlossomUser
from blossom.slack_conn.strings import help_message, summary_message

client = slack.WebClient(token=os.environ['SLACK_API_KEY'])


# https://stackoverflow.com/a/59043636
def fire_and_forget(f, *args, **kwargs):
    def wrapped(*args, **kwargs):
        threading.Thread(target=f, args=(args), kwargs=kwargs).start()

    return wrapped


def get_days():
    # the autoformatter thinks this is evil if it's all on one line.
    # Breaking it up a little for my own sanity.
    start_date = pytz.timezone("UTC").localize(
        timezone.datetime(day=1, month=4, year=2017), is_dst=None
    )

    return divmod((timezone.now() - start_date).days, 365)


def send_help_message(event):
    client.chat_postMessage(
        channel=event.get('channel'),
        text=f"{help_message}"
    )


def send_summary_message(event):
    client.chat_postMessage(
        channel=event.get('channel'),
        text=summary_message.format(
            BlossomUser.objects.filter(is_volunteer=True).count(),
            Transcription.objects.count(),
            get_days()[0],
            get_days()[1],
            "days" if get_days()[1] != 1 else "day"
        )

    )


@fire_and_forget
def process_message(data: Dict) -> None:
    e = data.get('event')

    try:
        # What comes in: "<@UTPFNCQS2> hello!"
        # Strip out the beginning section and see what's left.
        message = e['text'][e['text'].index('>') + 2:].lower()
    except IndexError:
        client.chat_postMessage(
            channel=e.get('channel'),
            text="Sorry, something went wrong and I couldn't parse your message."
        )
        return

    if not message:
        client.chat_postMessage(
            channel=e.get('channel'),
            text="Sorry, I wasn't able to get text out of that. Try again."
        )

    elif "help" in message:
        send_help_message(e)

    elif "summary" in message:
        send_summary_message(e)
