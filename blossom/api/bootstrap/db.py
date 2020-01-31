import logging

import pytz
import uuid
from datetime import datetime

from blossom.api.models import Transcription, Submission
from blossom.authentication.models import BlossomUser

logger = logging.getLogger(__name__)


def get_or_create_user(username):
    try:
        v = BlossomUser.objects.get(username=username)
        logger.info("Volunteer already exists! Pulled existing record.")
    except BlossomUser.DoesNotExist:
        # we'll set a random password; if they need it, we can reset it.
        v = BlossomUser.objects.create(
            username=username, accepted_coc=True, is_volunteer=True
        )
        v.set_unusable_password()
        v.save()
    return v


def get_or_create_transcription(
    post, volunteer, t_comment, comment_body, transcribot_text=None
):
    try:
        Transcription.objects.get(submission=post)
        logger.info("Found a matching transcription for that post!")
    except Transcription.DoesNotExist:
        logger.info(f"creating transcription {post.id}")
        Transcription.objects.create(
            submission=post,
            author=volunteer,
            post_time=datetime.utcfromtimestamp(t_comment.created_utc).replace(
                tzinfo=pytz.UTC
            ),
            transcription_id=t_comment.id,
            completion_method="reddit",
            url=f"https://reddit.com{t_comment.permalink}",
            text=comment_body,
            ocr_text=transcribot_text,
            removed_from_reddit=False,
        )


def get_or_create_post(tor_post, v, claim, done, redis_id):
    try:
        p = Submission.objects.get(submission_id=tor_post.id)
        logger.info("Found a matching post for a transcription ID!")
    except Submission.DoesNotExist:
        p = None
        # claim, done = get_tor_claim_and_done_from_pushshift(tor_post.id)
        logger.info(f"creating post {tor_post.id}")

        if claim is None:
            claim_time = None
        else:
            claim_time = datetime.utcfromtimestamp(claim.created_utc).replace(
                tzinfo=pytz.UTC
            )
        if done is None:
            complete_time = None
        else:
            complete_time = datetime.utcfromtimestamp(done.created_utc).replace(
                tzinfo=pytz.UTC
            )

        p = Submission.objects.create(
            submission_id=tor_post.id,
            submission_time=datetime.utcfromtimestamp(tor_post.created_utc).replace(
                tzinfo=pytz.UTC
            ),
            claimed_by=v,
            completed_by=v,
            redis_id=redis_id,
            claim_time=claim_time,
            complete_time=complete_time,
            source="reddit",
            url=tor_post.url,
            tor_url=f"https://reddit.com{tor_post.permalink}",
        )
    return p


def get_anon_user():
    return get_or_create_user("GrafeasAnonymousUser")


def generate_dummy_post(vlntr=None):
    logger.info(f"creating dummy post...")
    return Submission.objects.create(source="bootstrap_from_redis", completed_by=vlntr)


def generate_dummy_transcription(vlntr, post=None):
    """
    This can be for any volunteer, because especially for older volunteers,
    their official gamma count will not match the number of transcription
    IDs we have on file. Therefore, to pad the results and make sure that
    we keep an accurate count in the DB, we'll create dummy transcriptions
    in their name.

    :param vlntr: Volunteer instance
    :param post: optional; Post instance
    :return: None
    """
    if post is None:
        post = generate_dummy_post(vlntr)
    logger.info("Creating dummy transcription...")
    Transcription.objects.create(
        submission=post,
        author=vlntr,
        transcription_id=str(uuid.uuid4()),
        completion_method="bootstrap_from_redis",
        text="dummy transcription",
    )
