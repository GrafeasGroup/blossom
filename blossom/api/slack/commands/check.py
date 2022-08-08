from blossom.api.models import TranscriptionCheck
from blossom.api.slack import client
from blossom.api.slack.transcription_check.messages import send_check_message
from blossom.api.slack.utils import extract_url_from_link
from blossom.api.views.find import find_by_url, normalize_url
from blossom.strings import translation

i18n = translation()


def check_cmd(channel: str, message: str) -> None:
    """Generate a transcription check for a link."""
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
        if transcription := find_response.get("transcription"):
            # Does a check already exist for this transcription?
            if prev_check := TranscriptionCheck.objects.filter(
                transcription=transcription
            ).first():
                # Make sure that the check actually got sent to Slack
                if prev_check.slack_channel_id and prev_check.slack_message_ts:
                    response = client.chat_getPermalink(
                        channel=prev_check.slack_channel_id,
                        message_ts=prev_check.slack_message_ts,
                    )
                    permalink = response.data.get("permalink")

                    # Notify the user with a link to the existing check
                    client.chat_postMessage(
                        channel=channel,
                        text=i18n["slack"]["check"]["already_checked"].format(
                            check_url=permalink,
                            tr_url=transcription.url,
                            username=transcription.author.username,
                        ),
                        unfurl_links=False,
                        unfurl_media=False,
                    )
                    return

            # Create a new check object
            check = prev_check or TranscriptionCheck.objects.create(
                transcription=transcription, trigger="Manual check"
            )

            # Send the check to the check channel
            send_check_message(check)
            check.refresh_from_db()

            # Get the link for the check
            response = client.chat_getPermalink(
                channel=check.slack_channel_id,
                message_ts=check.slack_message_ts,
            )
            permalink = response.data.get("permalink")

            # Notify the user
            client.chat_postMessage(
                channel=channel,
                text=i18n["slack"]["check"]["success"].format(
                    check_url=permalink,
                    tr_url=transcription.url,
                    username=transcription.author.username,
                ),
                unfurl_links=False,
                unfurl_media=False,
            )
        else:
            # No transcription for post
            client.chat_postMessage(
                channel=channel,
                text=i18n["slack"]["check"]["no_transcription"].format(
                    tor_url=find_response["submission"].tor_url,
                ),
                unfurl_links=False,
                unfurl_media=False,
            )
            return
    else:
        # URL not found
        client.chat_postMessage(
            channel=channel,
            text=i18n["slack"]["check"]["no_submission"].format(url=normalized_url),
            unfurl_links=False,
            unfurl_media=False,
        )
        return
