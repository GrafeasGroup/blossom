from typing import Dict

from django.conf import settings

from blossom.api.slack import client
from blossom.api.slack.actions import i18n


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
    if action == "edited" or action == "tier_changed" or action == "pending_tier_change":
        emote = ":rotating_light:"
    username = data["sponsorship"]["sponsor"]["login"]
    sponsorlevel = data["sponsorship"]["tier"]["name"]

    msg = i18n["slack"]["github_sponsor_update"].format(emote, action, username, sponsorlevel)
    client.chat_postMessage(channel=settings.SLACK_GITHUB_SPONSORS_CHANNEL, text=msg)
