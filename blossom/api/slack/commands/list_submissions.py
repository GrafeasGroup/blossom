import zoneinfo
from datetime import datetime
from uuid import uuid4

from django.db.models import QuerySet
from slack.web.classes.blocks import *
from slack.web.classes.elements import *
from slack.web.classes.views import View

from blossom.api.models import Submission
from blossom.api.slack import client
from blossom.authentication.models import BlossomUser
from blossom.strings import translation

i18n = translation()


def fmt_date(date_obj: datetime.date) -> str:
    """Convert date or datetime into slack-compatible date string."""
    return date_obj.strftime("%Y-%m-%d")


def _build_message() -> View:
    """Create the modal view that will display in Slack."""
    return View(
        type="modal",
        title="Get Submissions",
        callback_id="submission_list_modal",
        submit=PlainTextObject(text="Submit"),
        close=PlainTextObject(text="Close"),
        blocks=[
            SectionBlock(
                fields=[
                    TextObject(
                        type="mrkdwn",
                        text=(
                            "Select the date range to search for transcriptions in. Keep in mind"
                            " that if your date range is too big, there might be a lot of returned"
                            " transcriptions."
                        ),
                    )
                ]
            ),
            InputBlock(
                block_id="username",
                label="Username",
                element=PlainTextInputElement(
                    placeholder="itsthejoker", action_id="username_input"
                ),
            ),
            SectionBlock(
                block_id="date_start",
                text=PlainTextObject(text="Start Date:"),
                accessory=DatePickerElement(
                    initial_date="2017-04-01",
                    action_id="select_start_date",
                ),
            ),
            SectionBlock(
                block_id="date_end",
                text=PlainTextObject(text="Start Date:"),
                accessory=DatePickerElement(
                    initial_date=fmt_date(datetime.now(tz=zoneinfo.ZoneInfo("UTC"))),
                    action_id="select_end_date",
                ),
            ),
        ],
    )


def _build_response_blocks(
    submissions: QuerySet[Submission],
    user: BlossomUser,
    start_date: datetime.date,
    end_date: datetime.date,
) -> list[Block]:
    if submissions.count() > 48:
        # can have a max of 50 blocks in a message, so we need to revert to regular text if we need
        # more than that
        return []
    response = [
        SectionBlock(
            text=MarkdownTextObject(
                text=(
                    f"Transcriptions by *{user.username}* from *{fmt_date(start_date)}*"
                    f" to *{fmt_date(end_date)}*:"
                )
            )
        ),
        DividerBlock(),
    ]
    for submission in submissions:
        if submission.tor_url:
            # this is a valid transcription and not one of the very old dummy ones.
            response += [
                SectionBlock(
                    text=MarkdownTextObject(
                        text=(
                            f"*{fmt_date(submission.complete_time)}*"
                            f" {submission.get_subreddit_name()} | {submission.title}"
                        )
                    ),
                    accessory=LinkButtonElement(text="Open on Reddit", url=submission.tor_url),
                )
            ]
        else:
            response += [
                SectionBlock(
                    text=MarkdownTextObject(
                        text=f"*{fmt_date(submission.complete_time)}* Dummy Submission"
                    ),
                )
            ]
    return response


def _build_raw_text_message(
    submissions: QuerySet[Submission],
    user: BlossomUser,
    start_date: datetime.date,
    end_date: datetime.date,
) -> str:
    resp = f"""Too many submissions returned, defaulting to text.\n\nTranscriptions by
         *{user.username}* from *{fmt_date(start_date)}* to *{fmt_date(end_date)}*:\n\n
        """
    for submission in submissions:
        if submission.tor_url:
            additional_submission = (
                f"*{fmt_date(submission.complete_time)}* {submission.get_subreddit_name()}"
                f" | {submission.title} | <{submission.tor_url}|ToR Post>"
            )
        else:
            additional_submission = f"*{fmt_date(submission.complete_time)}* | {submission.title}"
        resp += additional_submission
    return resp


def process_submission_list(data: dict) -> None:
    """Handle the form submission."""
    # This processes the modal listed above, so the structure is different from the usual
    # actions that we process. See
    # https://api.slack.com/reference/interaction-payloads/views#view_submission_example
    # for the response body.
    channel_id = data["view"]["response_urls"][0]["channel_id"]

    username: str = data["view"]["state"]["values"]["username"]["username_input"]["value"]
    start_date: datetime.date = datetime.strptime(
        data["view"]["state"]["values"]["date_start"]["select_start_date"]["value"], "%Y-%m-%d"
    ).replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
    end_date: datetime.date = datetime.strptime(
        data["view"]["state"]["values"]["date_end"]["select_end_date"]["value"], "%Y-%m-%d"
    ).replace(tzinfo=zoneinfo.ZoneInfo("UTC"))

    try:
        user = BlossomUser.objects.get(username=username)
    except BlossomUser.DoesNotExist:
        client.chat_postMessage(
            channel=channel_id,
            text=i18n["slack"]["errors"]["unknown_username"].format(username=username),
        )
        return

    submissions = Submission.objects.filter(
        completed_by=user, complete_time__gte=start_date, complete_time__lte=end_date
    )

    if submissions.count() == 0:
        client.chat_postMessage(
            channel=data["view"]["response_urls"][0]["channel_id"],
            text=i18n["slack"]["submissions"]["no_submissions"].format(
                username=username, start=fmt_date(start_date), end=fmt_date(end_date)
            ),
        )
        return

    blocks = _build_response_blocks(submissions, user, start_date, end_date)
    if blocks:
        client.chat_postMessage(channel=channel_id, blocks=blocks)
    else:
        client.chat_postMessage(
            channel=channel_id,
            text=_build_raw_text_message(submissions, user, start_date, end_date),
        )


def submissions_cmd(channel: str, _message: str) -> None:
    """Get information from a date range about submissions of a user."""
    client.views_open(trigger_id=str(uuid4()), view=_build_message())
