import zoneinfo
from datetime import datetime
from uuid import uuid4

from slack.web.classes.blocks import *
from slack.web.classes.elements import *
from slack.web.classes.views import View

from blossom.api.slack import client
from blossom.strings import translation

i18n = translation()


def _build_message() -> View:
    """Create the modal view that will display in Slack.

    Action IDs:

    * submission_list_username_input
    * submission_list_select_start_date
    * submission_list_select_end_date
    """
    return View(
        type="modal",
        title="Get Submissions",
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
                label="Username",
                element=PlainTextInputElement(
                    placeholder="itsthejoker", action_id="submission_list_username_input"
                ),
            ),
            SectionBlock(
                text=PlainTextObject(text="Start Date:"),
                accessory=DatePickerElement(
                    initial_date="2017-04-01",
                    action_id="submission_list_select_start_date",
                ),
            ),
            SectionBlock(
                text=PlainTextObject(text="Start Date:"),
                accessory=DatePickerElement(
                    initial_date=datetime.now(tz=zoneinfo.ZoneInfo("UTC")).strftime("%Y-%m-%d"),
                    action_id="submission_list_select_end_date",
                ),
            ),
        ],
    )


def _process_submission_list(data: dict) -> None:
    from pprint import pprint

    pprint(data)


def submissions_cmd(channel: str, _message: str) -> None:
    """Get information from a date range about submissions of a user."""
    client.views_open(trigger_id=uuid4(), view=_build_message())
