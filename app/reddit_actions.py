import logging
from contextlib import suppress

import praw.exceptions
from django.http import HttpRequest

from api.models import Submission, Transcription
from blossom.reddit import REDDIT
from utils.workers import send_to_worker

log = logging.getLogger(__name__)


BASE_URL = "https://reddit.com"


class Flair:
    unclaimed = "Unclaimed"
    summoned_unclaimed = "Summoned - Unclaimed"
    completed = "Completed!"
    in_progress = "In Progress"
    meta = "Meta"
    disregard = "Disregard"


@send_to_worker
def submit_transcription(
    request: HttpRequest, transcription_obj: Transcription, submission_obj: Submission
) -> None:
    """Post the transcription to Reddit as the user."""
    reddit_submission = request.user.reddit.submission(url=submission_obj.url)
    transcription = reddit_submission.reply(transcription_obj.text)
    transcription_obj.original_id = transcription.fullname
    transcription_obj.url = BASE_URL + transcription.permalink
    transcription_obj.removed_from_reddit = False
    transcription_obj.save()


@send_to_worker
def edit_transcription(
    request: HttpRequest, transcription_obj: Transcription, submission_obj: Submission
) -> None:
    """Post the updated transcription as an edit to the existing comment."""
    url = transcription_obj.url
    if not url:
        # Something went wrong; it was never pushed in the first place.
        # Try it again.
        submit_transcription(request, transcription_obj, submission_obj)
        return

    if BASE_URL not in url:
        url = BASE_URL + url

    reddit_comment = request.user.reddit.comment(url=url)
    with suppress(praw.exceptions.RedditAPIException):
        reddit_comment.edit(transcription_obj.text)


@send_to_worker
def remove_post(submission_obj: Submission) -> None:
    """Remove the requested post from the r/ToR queue."""
    log.info(f"Removing {submission_obj.original_id} from r/ToR.")
    REDDIT.submission(url=submission_obj.tor_url).mod.remove()


@send_to_worker
def flair_post(submission_obj: Submission, text: str) -> None:
    """Change the flair of the requested post on the r/ToR queue."""
    tor_submission = REDDIT.submission(url=submission_obj.tor_url)
    for choice in tor_submission.flair.choices():
        if choice["flair_text"] == text:
            log.info(f"Flairing post {submission_obj.original_id} with {text}")
            tor_submission.flair.select(flair_template_id=choice["flair_template_id"])
            return

    # if the flairing is successful, we won't hit this line.
    log.error(f"Cannot find requested flair {text}. Not flairing.")


@send_to_worker
def advertise(submission_obj: Submission) -> None:
    """Post a message explaining how this submission was completed to r/ToR."""
    reddit_submission = REDDIT.submission(url=submission_obj.tor_url)
    reddit_submission.reply("This post was completed using TheTranscription.App!")
