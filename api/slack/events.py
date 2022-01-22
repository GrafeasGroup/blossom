import binascii
import hashlib
import hmac
import logging
import time
from typing import Dict

from django.conf import settings
from django.http import HttpRequest

from api.models import Submission
from api.slack import client
from app.reddit_actions import remove_post
from blossom.strings import translation
from utils.workers import send_to_worker

logger = logging.getLogger("api.slack.events")

i18n = translation()


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
    client.chat_postMessage(channel=settings.SLACK_GITHUB_SPONSORS_CHANNEL, text=msg)


def process_submission_update(data: dict) -> None:
    """Remove the submission from both reddit and app if it needs to be removed."""
    # Blocks are created using the Slack Block Kit Builder
    # https://app.slack.com/block-kit-builder/
    value = data["actions"][0].get("value").split("_")
    blocks = data["message"]["blocks"]
    submission_obj = Submission.objects.get(id=int(value[2]))
    if value[0] == "keep":
        submission_obj.removed_from_queue = False
        submission_obj.save(skip_extras=True)
        blocks[-1] = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Thank you! This submission has been kept.",
            },
        }
    else:
        # Remove the post from Reddit
        remove_post(submission_obj)
        # Make sure the submission is marked as removed
        # If reported on the app side this already happened, but not for
        # reports from Reddit
        submission_obj.removed_from_queue = True
        submission_obj.save(skip_extras=True)

        blocks[-1] = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"Submission ID {submission_obj.id} has been removed from the queue."
                ),
            },
        }

    client.chat_update(
        channel=data["channel"]["id"], ts=data["message"]["ts"], blocks=blocks
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


def is_valid_slack_request(request: HttpRequest) -> bool:
    """Verify that a webhook from Slack is actually from them."""
    # adapted from https://api.slack.com/authentication/verifying-requests-from-slack
    if (slack_signature := request.headers.get("X-Slack-Signature")) is None:
        return False

    timestamp = request.headers["X-Slack-Request-Timestamp"]
    if abs(time.time() - int(timestamp)) > 60 * 5:
        # The request timestamp is more than five minutes from local time.
        # It could be a replay attack, so let's ignore it.
        return False

    sig_basestring = "v0:" + timestamp + ":" + request.body.decode()

    signature = (
        "v0="
        + hmac.new(
            bytes(settings.SLACK_SIGNING_SECRET, "latin-1"),
            msg=bytes(sig_basestring, "latin-1"),
            digestmod=hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(signature, slack_signature)


@send_to_worker
def ask_about_removing_post(submission: Submission, reason: str) -> None:
    """Ask Slack if we want to remove a reported submission or not."""
    # Check if this got already sent to mod chat, we don't want duplicates
    if (
        submission.report_slack_channel_id is not None
        or submission.report_slack_message_ts is not None
    ):
        return

    report_text = (
        "Submission: <{url}|{title}> | <{tor_url}|ToR Post>\nReport reason: {reason}"
    ).format(
        url=submission.url,
        title=submission.title,
        tor_url=submission.tor_url,
        reason=reason,
    )
    keep_submission = f"keep_submission_{submission.id}"
    remove_submission = f"remove_submission_{submission.id}"

    # created using the Slack Block Kit Builder https://app.slack.com/block-kit-builder/
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "This submission was reported -- please investigate and decide"
                    " whether it should be removed."
                ),
            },
        },
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": report_text}},
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Keep"},
                    "value": keep_submission,
                },
                {
                    "type": "button",
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Remove"},
                    "value": remove_submission,
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Are you sure?"},
                        "text": {
                            "type": "mrkdwn",
                            "text": "This will remove the submission from the queue.",
                        },
                        "confirm": {"type": "plain_text", "text": "Nuke it"},
                        "deny": {"type": "plain_text", "text": "Back"},
                    },
                },
            ],
        },
    ]

    response = client.chat_postMessage(
        channel=settings.SLACK_REPORTED_POST_CHANNEL, blocks=blocks
    )
    if not response["ok"]:
        logger.warning(
            f"Could not send report for submission {submission.id} to Slack!"
        )
        return

    # See https://api.slack.com/methods/chat.postMessage
    submission.report_slack_channel_id = response["channel"]
    submission.report_slack_message_ts = response["message"]["ts"]
    submission.save()
