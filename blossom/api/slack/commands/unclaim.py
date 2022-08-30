from blossom.api.slack import client
from blossom.api.slack.utils import extract_url_from_link
from blossom.api.views.find import find_by_url, normalize_url
from blossom.strings import translation

i18n = translation()


def unclaim_cmd(channel: str, message: str) -> None:
    """Forcibly unclaim a post from a user."""
    parsed_message = message.split()

    if len(parsed_message) == 1:
        # URL not provided
        msg = i18n["slack"]["check"]["no_url"]
        client.chat_postMessage(channel=channel, text=msg)
        return
    if len(parsed_message) > 2:
        # Too many parameters
        msg = i18n["slack"]["errors"]["too_many_params"]
        client.chat_postMessage(channel=channel, text=msg)
        return

    url = parsed_message[1]
    normalized_url = normalize_url(extract_url_from_link(url))

    # Check if the URL is valid
    if normalized_url is None:
        client.chat_postMessage(
            channel=channel,
            text=i18n["slack"]["check"]["invalid_url"].format(url=url),
            unfurl_links=False,
            unfurl_media=False,
        )
        return

    if find_response := find_by_url(normalized_url):
        submission = find_response.get("submission")

        if submission.claimed_by is None:
            # FIXME: Send error message
            return
        if submission.completed_by is not None:
            # FIXME: Send error message
            return

        # FIXME: Ask mod for confirmation

        # Actually unclaim the submission
        submission.claimed_by = None
        submission.claim_time = None
        submission.save()

        # FIXME: Send confirmation message

        # FIXME: Send message to mod that the post was unclaimed?
    else:
        # URL not found
        client.chat_postMessage(
            channel=channel,
            text=i18n["slack"]["check"]["no_submission"].format(url=normalized_url),
            unfurl_links=False,
            unfurl_media=False,
        )
        return
