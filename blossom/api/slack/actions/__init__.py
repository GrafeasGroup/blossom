import binascii
import hashlib
import hmac
import logging
import time
from typing import Dict

from django.conf import settings
from django.http import HttpRequest

from blossom.api.slack import client
from blossom.api.slack.actions.report import process_submission_report_update
from blossom.api.slack.commands.migrate_user import process_migrate_user
from blossom.api.slack.transcription_check.actions import process_check_action

from blossom.strings import translation

logger = logging.getLogger("blossom.api.slack.actions")
i18n = translation()


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
