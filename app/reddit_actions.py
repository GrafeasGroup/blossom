import logging

from api.models import Submission
from blossom.reddit import REDDIT
from utils.workers import send_to_worker

log = logging.getLogger(__name__)


class Flair:
    unclaimed = "Unclaimed"
    summoned_unclaimed = "Summoned - Unclaimed"
    completed = "Completed!"
    in_progress = "In Progress"
    meta = "Meta"
    disregard = "Disregard"


@send_to_worker
def remove_post(submission_obj: Submission) -> None:
    """Remove the requested post from the r/ToR queue."""
    log.info(f"Removing {submission_obj.original_id} from r/ToR.")
    REDDIT.submission(url=submission_obj.url).mod.remove()


@send_to_worker
def flair_post(submission_obj: Submission, text: str) -> None:
    """Change the flair of the requested post on the r/ToR queue."""
    reddit_submission = REDDIT.submission(url=submission_obj.url)
    for choice in reddit_submission.flair.choices():
        if choice["flair_text"] == text:
            log.info(f"Flairing post {submission_obj.original_id} with {text}")
            reddit_submission.flair.select(
                flair_template_id=choice["flair_template_id"]
            )
            return

    # if the flairing is successful, we won't hit this line.
    log.error(f"Cannot find requested flair {text}. Not flairing.")
