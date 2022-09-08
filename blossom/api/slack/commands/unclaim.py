from blossom.api.slack import client
from blossom.api.slack.messages.unclaim import (
    get_ask_confirmation_blocks,
    get_ask_confirmation_text,
)
from blossom.api.slack.utils import extract_url_from_link
from blossom.api.views.find import find_by_url, normalize_url
from blossom.strings import translation

i18n = translation()


def unclaim_cmd(channel: str, message: str) -> None:
    """Forcibly unclaim a post from a user."""
    parsed_message = message.split()

    if len(parsed_message) == 1:
        # URL not provided
        msg = i18n["slack"]["unclaim"]["no_url"]
        client.chat_postMessage(channel=channel, text=msg)
        return
    if len(parsed_message) > 2:
        # Too many parameters
        msg = i18n["slack"]["errors"]["too_many_params"]
        client.chat_postMessage(channel=channel, text=msg)
        return

    original_url = parsed_message[1]
    normalized_url = normalize_url(extract_url_from_link(original_url))

    # Check if the URL is valid
    if normalized_url is None:
        client.chat_postMessage(
            channel=channel,
            text=i18n["slack"]["errors"]["invalid_url"].format(url=original_url),
            unfurl_links=False,
            unfurl_media=False,
        )
        return

    if find_response := find_by_url(normalized_url):
        submission = find_response.get("submission")

        tor_url = submission.tor_url

        if submission.claimed_by is None:
            # Nobody claimed this submission, abort
            client.chat_postMessage(
                channel=channel,
                text=i18n["slack"]["unclaim"]["not_claimed"].format(tor_url=tor_url),
                unfurl_links=False,
                unfurl_media=False,
            )
            return

        user = submission.claimed_by
        username = user.username

        if submission.completed_by is not None:
            # The submission is already completed, abort
            client.chat_postMessage(
                channel=channel,
                text=i18n["slack"]["unclaim"]["already_completed"].format(
                    tor_url=tor_url, username=username
                ),
                unfurl_links=False,
                unfurl_media=False,
            )
            return

        # Send a message with buttons, to ask the mod for confirmation
        # The actual unclaiming is handled in the Slack action that is sent from the button
        client.chat_postMessage(
            channel=channel,
            blocks=get_ask_confirmation_blocks(submission, user),
            text=get_ask_confirmation_text(),
        )
    else:
        # URL not found
        client.chat_postMessage(
            channel=channel,
            text=i18n["slack"]["check"]["no_submission"].format(url=normalized_url),
            unfurl_links=False,
            unfurl_media=False,
        )
        return
