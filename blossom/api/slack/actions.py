import binascii
import hashlib
import hmac
import logging
import time
from enum import Enum
from typing import Dict, List

from django.conf import settings
from django.http import HttpRequest

from blossom.api.models import Submission
from blossom.api.slack import client
from blossom.api.slack.commands.migrate_user import process_migrate_user
from blossom.api.slack.transcription_check.actions import process_check_action
from blossom.app.reddit_actions import approve_post, remove_post
from blossom.strings import translation
from blossom.utils.workers import send_to_worker

logger = logging.getLogger("blossom.api.slack.events")

i18n = translation()


class ReportMessageStatus(Enum):
    """The current status of the report."""

    REPORTED = "reported"
    REMOVED = "removed"
    APPROVED = "approved"


def process_action(data: Dict) -> None:
    """Process a Slack action, e.g. a button press."""
    value: str = data["actions"][0].get("value")
    if value.startswith("check"):
        process_check_action(data)
    elif "submission" in value:
        # buttons related to approving or removing submissions on the app and on Reddit
        process_submission_report_update(data)
    elif "migration" in value:
        # buttons related to account gamma migrations
        process_migrate_user(data)
    else:
        client.chat_postMessage(
            channel=data["channel"]["id"],
            text=i18n["slack"]["errors"]["unknown_payload"].format(value),
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

    msg = i18n["slack"]["github_sponsor_update"].format(
        emote, action, username, sponsorlevel
    )
    client.chat_postMessage(channel=settings.SLACK_GITHUB_SPONSORS_CHANNEL, text=msg)


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
    if submission.has_slack_report_message:
        return

    submission.report_reason = reason
    submission.save(skip_extras=True)

    response = client.chat_postMessage(
        channel=settings.SLACK_REPORTED_POST_CHANNEL,
        blocks=_construct_report_message_blocks(
            submission, ReportMessageStatus.REPORTED
        ),
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


def process_submission_report_update(data: dict) -> None:
    """Remove the submission from both reddit and app if it needs to be removed."""
    # Blocks are created using the Slack Block Kit Builder
    # https://app.slack.com/block-kit-builder/
    value = data["actions"][0].get("value")
    channel_id = data["channel"]["id"]
    message_ts = data["message"]["ts"]

    # Find the submission corresponding to the message
    submissions = Submission.objects.filter(
        report_slack_channel_id=channel_id,
        report_slack_message_ts=message_ts,
    )

    if len(submissions) == 0:
        logger.warning(
            f"No submission found for value {value}, channel ID {channel_id} "
            f"and message TS {message_ts}."
        )
        return

    submission = submissions[0]
    action = value.split("_")[0]

    # Determine the new report status
    if action == "approve":
        status = ReportMessageStatus.APPROVED
    elif action == "remove":
        status = ReportMessageStatus.REMOVED
    else:
        logger.warning(f"Invalid report action {action}.")
        return

    update_submission_report(submission, status)


def update_submission_report(
    submission: Submission, status: ReportMessageStatus
) -> None:
    """Update the report of the given submission to the new status."""
    if status == ReportMessageStatus.APPROVED:
        # Approve the post on Reddit
        approve_post(submission)
        # Make sure the submission isn't marked as removed
        submission.removed_from_queue = False
        submission.approved = True
        submission.save(skip_extras=True)

        blocks = _construct_report_message_blocks(
            submission, ReportMessageStatus.APPROVED
        )
    elif status == ReportMessageStatus.REMOVED:
        # Remove the post from Reddit
        remove_post(submission)
        # Make sure the submission is marked as removed
        # If reported on the app side this already happened, but not for
        # reports from Reddit
        submission.removed_from_queue = True
        submission.approved = False
        submission.save(skip_extras=True)

        blocks = _construct_report_message_blocks(
            submission, ReportMessageStatus.REMOVED
        )
    elif status == ReportMessageStatus.REPORTED:
        # A fresh report
        blocks = _construct_report_message_blocks(
            submission, ReportMessageStatus.REPORTED
        )
    else:
        logger.warning(f"Unknown submission update {status}!")
        return

    client.chat_update(
        channel=submission.report_slack_channel_id,
        ts=submission.report_slack_message_ts,
        blocks=blocks,
    )


def _construct_report_message_blocks(
    submission: Submission, status: ReportMessageStatus
) -> List[Dict]:
    """Construct the report message for the given submission."""
    post_status = (
        f"Completed by u/{submission.completed_by.username}"
        if submission.completed_by
        else f"Claimed by u/{submission.claimed_by.username}"
        if submission.claimed_by
        else "Unclaimed"
    )
    report_text = f"*<{submission.url}|{submission.title}>* (`#{submission.id}`)\n"
    report_text += f"<{submission.tor_url}|ToR Post> | {post_status}\n\n"
    report_text += f"*Report reason*: {submission.report_reason}"

    status_text = _construct_report_message_status_text(status)
    actions = _construct_report_message_actions(submission, status)

    # created using the Slack Block Kit Builder https://app.slack.com/block-kit-builder/
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": report_text},
            "accessory": {
                "type": "image",
                "image_url": submission.content_url,
                "alt_text": f"Image of submission {submission.id}",
            },
        },
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": status_text}},
        {"type": "actions", "elements": actions},
    ]


def _construct_report_message_status_text(status: ReportMessageStatus) -> str:
    """Get the status text for the report message."""
    if status == ReportMessageStatus.REPORTED:
        return "What should we do with this submission?"
    elif status == ReportMessageStatus.REMOVED:
        return "The submission has been *removed*."
    elif status == ReportMessageStatus.APPROVED:
        return "The submission has been *approved*."
    else:
        raise RuntimeError(f"Unexpected report status {status}!")


def _construct_report_message_actions(
    submission: Submission, status: ReportMessageStatus
) -> List[Dict]:
    """Construct the actions (buttons) for a report message."""
    if status == ReportMessageStatus.REPORTED:
        return [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Approve"},
                "value": f"approve_submission_{submission.id}",
            },
            {
                "type": "button",
                "style": "danger",
                "text": {"type": "plain_text", "text": "Remove"},
                "value": f"remove_submission_{submission.id}",
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
        ]
    elif status == ReportMessageStatus.REMOVED:
        return [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Revert"},
                "value": f"approve_submission_{submission.id}",
                "confirm": {
                    "title": {"type": "plain_text", "text": "Are you sure?"},
                    "text": {
                        "type": "mrkdwn",
                        "text": "This will revert the removal by *approving* the post.",
                    },
                    "confirm": {"type": "plain_text", "text": "Approve"},
                    "deny": {"type": "plain_text", "text": "Back"},
                },
            },
        ]
    elif status == ReportMessageStatus.APPROVED:
        return [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Revert"},
                "value": f"remove_submission_{submission.id}",
                "confirm": {
                    "title": {"type": "plain_text", "text": "Are you sure?"},
                    "text": {
                        "type": "mrkdwn",
                        "text": "This will revert the approval by *removing* the post.",
                    },
                    "confirm": {"type": "plain_text", "text": "Remove"},
                    "deny": {"type": "plain_text", "text": "Back"},
                },
            },
        ]
    else:
        raise RuntimeError(f"Unexpected report status {status}!")
