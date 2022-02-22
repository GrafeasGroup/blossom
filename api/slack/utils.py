import logging
import re
from typing import Dict, List, Optional

from django.conf import settings
from slack import WebClient

from api.models import Submission, Transcription
from authentication.models import BlossomUser
from blossom.strings import translation

logger = logging.getLogger("api.slack.utils")

i18n = translation()


# find a link in the slack format, then strip out the text at the end.
# they're formatted like this: <https://example.com|Text!>
SLACK_TEXT_EXTRACTOR = re.compile(
    r"<(?:https?://)?[\w-]+(?:\.[\w-]+)+\.?(?::\d+)?(?:/\S*)?\|([^>]+)>"
)


def clean_links(text: str) -> str:
    """Strip link out of auto-generated slack fancy URLS and return the text only."""
    results = [_ for _ in re.finditer(SLACK_TEXT_EXTRACTOR, text)]
    # we'll replace things going backwards so that we don't mess up indexing
    results.reverse()

    for match in results:
        text = text[: match.start()] + match.groups()[0] + text[match.end() :]
    return text


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


def get_message(data: Dict) -> Optional[str]:
    """
    Pull message text out of slack event.

    What comes in: "<@UTPFNCQS2> hello!" Strip out the beginning section
    and see what's left.
    """
    event = data.get("event")
    # Note: black and flake8 disagree on the formatting. Black wins.
    try:
        return event["text"][event["text"].index(">") + 2 :].lower()  # noqa: E203
    except IndexError:
        return None


def _send_transcription_to_slack(
    transcription: Transcription,
    submission: Submission,
    user: BlossomUser,
    slack_client: WebClient,
    reason: str,
) -> None:
    """Notify slack for the transcription check."""
    gamma = user.gamma
    msg = f"*Transcription check* for u/{user.username} ({user.gamma:,d}:)\n"

    # Add relevant links
    tor_url = (
        "<{}|ToR Post>".format(submission.tor_url) if submission.tor_url else "[N/A]"
    )
    post_url = "<{}|Partner Post>".format(submission.url) if submission.url else "[N/A]"
    transcription_url = (
        "<{}|Transcription>".format(transcription.url)
        if transcription.url and not transcription.removed_from_reddit
        else "[Removed]"
    )
    msg += " | ".join([tor_url, post_url, transcription_url]) + "\n"

    # Add check reason
    msg += f"Reason: {reason}\n"

    # Is it the first transcription? Extra care has to be taken
    if gamma == 1:
        msg += ":rotating_light: First transcription! :rotating_light:"

    try:
        slack_client.chat_postMessage(
            channel=settings.SLACK_TRANSCRIPTION_CHECK_CHANNEL, text=msg.strip(),
        )
    except:  # noqa
        logger.warning(f"Cannot post message to slack. Msg: {msg}")
