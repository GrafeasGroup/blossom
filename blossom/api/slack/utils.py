import logging
import re
from re import Match
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from slack import WebClient

from blossom.api.models import Submission
from blossom.authentication.models import BlossomUser
from blossom.strings import translation

logger = logging.getLogger("blossom.api.slack.utils")

i18n = translation()


# find a link in the slack format, then strip out the text at the end.
# they're formatted like this: <https://example.com|Text!>
SLACK_TEXT_EXTRACTOR = re.compile(
    # Allow long lines for the regex
    # flake8: noqa: E501
    r"<(?P<url>(?:https?://)?[\w-]+(?:\.[\w-]+)+\.?(?::\d+)?(?:/[^\s|]*)?)(?:\|(?P<text>[^>]+))?>"
)

BOLD_REGEX = re.compile(r"\*(?P<content>[^*]+)\*")

USERNAME_REGEX = re.compile(r"(?:/?u/)?(?P<username>\S+)")


def extract_text_from_link(text: str) -> str:
    """Strip link out of auto-generated slack fancy URLS and return the text only."""
    results = [_ for _ in re.finditer(SLACK_TEXT_EXTRACTOR, text)]
    # we'll replace things going backwards so that we don't mess up indexing
    results.reverse()

    def extract_text(mx: Match) -> str:
        return mx["text"] or mx["url"]

    for match in results:
        text = text[: match.start()] + extract_text(match) + text[match.end() :]
    return text


def extract_url_from_link(text: str) -> str:
    """Strip link out of auto-generated slack fancy URLS and return the link only."""
    results = [_ for _ in re.finditer(SLACK_TEXT_EXTRACTOR, text)]
    # we'll replace things going backwards so that we don't mess up indexing
    results.reverse()

    def extract_link(m: Match) -> str:
        return m["url"]

    for match in results:
        text = text[: match.start()] + extract_link(match) + text[match.end() :]
    return text


def parse_user(text: str) -> Tuple[Optional[BlossomUser], str]:
    """Parse a username argument of a Slack command to a user object.

    This takes care of link formatting, bold formatting and the u/ prefix.
    Returns `None` if the user couldn't be found.
    """
    # Remove link formatting
    username = extract_text_from_link(text)

    # Remove bold formatting
    bold_match = BOLD_REGEX.match(username)
    if bold_match:
        username = bold_match.group("content")

    # Remove u/ prefix
    prefix_match = USERNAME_REGEX.match(username)
    if prefix_match:
        username = prefix_match.group("username")

    # Try to fetch the given user
    user = BlossomUser.objects.filter(username=username).first()

    # Fix capitalization if user has been found
    if user:
        username = user.username

    return user, username


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


def get_reddit_username(slack_client: WebClient, user: Dict) -> Optional[str]:
    """Get the Reddit username for the given Slack user."""
    response = slack_client.users_profile_get(user=user.get("id"))
    if response.get("ok"):
        profile = response.get("profile", {})
        # First try to get the username from the custom Slack field.
        username = (
            profile.get("fields", {})
            .get(settings.SLACK_USERNAME_FIELD_KEY, {})
            .get("value")
        )
        # If this is not defined, take the display name instead.
        username = username or profile.get("display_name")

        # Extract the username if it has the u/ prefix
        match = USERNAME_REGEX.match(username)
        if match:
            username = match.group("username")

        return username
    else:
        return None


def get_source(submission: Submission) -> str:
    """Extract the source from the given submission."""
    if submission.url and "reddit.com" in submission.url:
        return "r/" + submission.url.split("/")[4]
    else:
        return submission.source.name
