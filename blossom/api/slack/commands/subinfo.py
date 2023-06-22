from datetime import datetime, timedelta

from django.db.models import Count
from django.utils import timezone

from blossom.api.models import Submission
from blossom.api.slack import client
from blossom.api.slack.utils import parse_subreddit
from blossom.authentication.models import BlossomUser
from blossom.strings import translation

i18n = translation()


QUEUE_TIMEOUT = timedelta(hours=18)


def subinfo_cmd(channel: str, message: str) -> None:
    """Send info about a subreddit to slack."""
    parsed_message = message.split()
    if len(parsed_message) == 1:
        # The subreddit name is missing
        client.chat_postMessage(
            channel=channel,
            text=i18n["slack"]["errors"]["unknown_username"].format(
                action="subinfo", argument="<subreddit>"
            ),
        )
        return

    elif len(parsed_message) == 2:
        subreddit = parse_subreddit(parsed_message[1])

        # Check if the sub exists in our system
        sub_submissions = Submission.objects.filter(feed__iexact=f"/r/{subreddit}")

        if sub_submissions.count() == 0:
            client.chat_postMessage(
                channel=channel,
                text=i18n["slack"]["errors"]["unknown_subreddit"].format(
                    subreddit=subreddit,
                ),
            )
            return

        # Get the correct capitalization for the subreddit
        subreddit = parse_subreddit(sub_submissions.first().feed)

        msg = sub_info_text(subreddit)
    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    client.chat_postMessage(channel=channel, text=msg)


def sub_info_text(subreddit: str) -> str:
    """Get the info message for the given subreddit."""
    prefixed_sub = f"/r/{subreddit}"

    queue_timeout = datetime.now(tz=timezone.utc) - QUEUE_TIMEOUT

    # Submission info

    query_all = Submission.objects.filter(removed_from_queue=False)
    query_sub = query_all.filter(feed__iexact=prefixed_sub)
    query_all_queue = query_all.filter(created_at__gte=queue_timeout, archived=False)
    query_sub_queue = query_all_queue.filter(feed__iexact=prefixed_sub)

    total_all = query_all.count()
    total_sub = query_sub.count()
    total_percentage = total_sub / total_all if total_all > 0.0 else 0.0

    queue_all = query_all_queue.count()
    queue_sub = query_sub_queue.count()
    queue_percentage = queue_all / queue_sub if queue_sub > 0.0 else 0.0

    submission_info = i18n["slack"]["subinfo"]["submission_info"].format(
        total_sub=total_sub,
        total_percentage=total_percentage,
        queue_sub=queue_sub,
        queue_percentage=queue_percentage,
    )

    # Transcription info

    query_all_transcribed = query_all.filter(completed_by__isnull=False)
    query_sub_transcribed = query_sub.filter(completed_by__isnull=False)

    transcribed_all = query_all_transcribed.count()
    transcribed_sub = query_sub_transcribed.count()
    transcribed_percentage_transcriptions = transcribed_sub / transcribed_all
    transcribed_percentage_sub_submissions = transcribed_sub / total_sub

    transcription_info = i18n["slack"]["subinfo"]["transcription_info"].format(
        transcribed_sub=transcribed_sub,
        transcribed_percentage_transcriptions=transcribed_percentage_transcriptions,
        transcribed_percentage_sub_submissions=transcribed_percentage_sub_submissions,
    )

    # Volunteer info

    volunteers_all = BlossomUser.objects.filter(is_bot=False).count()
    volunteers_sub = Submission.objects.filter(
        completed_by__isnull=False, feed__iexact=prefixed_sub
    ).aggregate(Count("completed_by__id", distinct=True))["completed_by__id__count"]
    volunteer_percentage = volunteers_sub / volunteers_all

    volunteer_info = i18n["slack"]["subinfo"]["volunteer_info"].format(
        volunteer_sub=volunteers_sub,
        volunteer_percentage=volunteer_percentage,
    )

    # Putting it all together
    return i18n["slack"]["subinfo"]["message"].format(
        subreddit=subreddit,
        submission_info=submission_info,
        transcription_info=transcription_info,
        volunteer_info=volunteer_info,
    )
