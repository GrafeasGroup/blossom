import logging
import uuid
from datetime import datetime

import prawcore
import pytz

from api.models import Source, Submission, Transcription
from authentication.models import BlossomUser
from blossom.reddit import REDDIT

logger = logging.getLogger(__name__)

SOURCE = Source.objects.get(name="reddit")


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
    post,
    volunteer,
    t_comment,
    comment_body,
    transcribot_text=None,
    transcribot_comment=None,
):
    try:
        Transcription.objects.get(submission=post)
        logger.info("Found a matching transcription for that post!")
    except Transcription.DoesNotExist:
        logger.info(f"creating transcription {post.id}")
        Transcription.objects.create(
            submission=post,
            author=volunteer,
            create_time=datetime.utcfromtimestamp(t_comment.created_utc).replace(
                tzinfo=pytz.UTC
            ),
            original_id=t_comment.id,
            source=SOURCE,
            url=f"https://reddit.com{t_comment.permalink}",
            text=comment_body,
            removed_from_reddit=False,
        )
        if transcribot_comment:
            logger.info(f"creating OCR transcription on {post.id}")
            Transcription.objects.create(
                submission=post,
                author=BlossomUser.objects.get(username="transcribot"),
                create_time=datetime.utcfromtimestamp(
                    transcribot_comment.created_utc
                ).replace(tzinfo=pytz.UTC),
                original_id=transcribot_comment.id,
                source=SOURCE,
                url=f"https://reddit.com{transcribot_comment.permalink}",
                text=transcribot_text,
                removed_from_reddit=False,
            )


def get_or_create_post(tor_post, v, claim, done, redis_id):
    try:
        p = Submission.objects.get(original_id=tor_post.id)
        logger.info("Found a matching post for a transcription ID!")
    except Submission.DoesNotExist:
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

        try:
            image_url = REDDIT.submission(url=tor_post.url).url
        except (prawcore.exceptions.Forbidden, prawcore.exceptions.NotFound):
            image_url = None

        p = Submission.objects.create(
            original_id=tor_post.id,
            create_time=datetime.utcfromtimestamp(tor_post.created_utc).replace(
                tzinfo=pytz.UTC
            ),
            claimed_by=v,
            completed_by=v,
            redis_id=redis_id,
            claim_time=claim_time,
            complete_time=complete_time,
            source=SOURCE,
            url=tor_post.url,
            tor_url=f"https://reddit.com{tor_post.permalink}",
            content_url=image_url,
        )
    return p


def get_anon_user():
    return get_or_create_user("GrafeasAnonymousUser")


def generate_dummy_post(vlntr=None):
    logger.info(f"creating dummy post...")
    return Submission.objects.create(
        source=Source.objects.get_or_create(name="bootstrap_from_redis")[0],
        completed_by=vlntr,
    )


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
        original_id=str(uuid.uuid4()),
        source=Source.objects.get_or_create(name="bootstrap_from_redis")[0],
        text="dummy transcription",
    )
