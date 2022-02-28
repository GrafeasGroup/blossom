import logging
from typing import Dict, Optional

from django.conf import settings

from api.models import TranscriptionCheck
from api.slack import client
from api.slack.transcription_check.blocks import construct_transcription_check_blocks

logger = logging.getLogger("api.slack.transcription_check.messages")


def send_check_message(
    check: TranscriptionCheck, channel: str = settings.SLACK_TRANSCRIPTION_CHECK_CHANNEL
) -> Optional[Dict]:
    """Send a transcription check message to the given channel."""
    blocks = construct_transcription_check_blocks(check)
    response = client.chat_postMessage(channel=channel, blocks=blocks)
    if not response["ok"]:
        logger.error(f"Could not send check {check.id} to Slack!")
        return None

    # See https://api.slack.com/methods/chat.postMessage
    check.slack_channel_id = response["channel"]
    check.slack_message_ts = response["message"]["ts"]
    check.save()

    return response


def update_check_message(check: TranscriptionCheck) -> None:
    """Update a transcription check message."""
    if check.slack_channel_id is None or check.slack_message_ts is None:
        # Something must have gone wrong when sending the last check, try again
        logging.warning(
            f"Slack properties missing for check {check.id}, sending it again..."
        )
        send_check_message(check)
        return

    blocks = construct_transcription_check_blocks(check)
    response = client.chat_update(
        channel=check.slack_channel_id, ts=check.slack_message_ts, blocks=blocks,
    )
    if not response["ok"]:
        logger.error(f"Could not update check {check.id} on Slack!")


def reply_to_action(data: Dict, text: str) -> Dict:
    """Reply to the given action with the given text."""
    channel_id = data["channel"]["id"]
    message_ts = data.get("message", {}).get("ts")

    return client.chat_postMessage(channel=channel_id, thread_ts=message_ts, text=text)


def reply_to_action_with_ping(data: Dict, text: str) -> Dict:
    """Reply to the given action with the given text and ping the user."""
    user_id = data["user"]["id"]

    return reply_to_action(data, f"<@{user_id}>, {text}")
