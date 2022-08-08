import logging
import uuid
from typing import Dict

import prawcore
from blossom_wrapper import BlossomStatus

from blossom.bootstrap import REDDIT, blossom

logger = logging.getLogger(__name__)


def get_or_create_user(username):
    v = blossom.get_user(username)
    if v.status == BlossomStatus.not_found:
        # we'll just grab the newly created user, even though it doesn't have
        # the accepted_coc flag set, because we can just use it and not worry
        # about it
        v = blossom.create_user(username)
        blossom.accept_coc(username)
    if v.status == BlossomStatus.ok:
        return v
    else:
        raise Exception(f"something went wrong: {v}")


def get_or_create_transcription(
    post,
    volunteer,
    t_comment,
    comment_body,
    transcribot_text=None,
    transcribot_comment=None,
):
    transcription = blossom.get_transcription(submission=post["id"])
    if transcription.status == BlossomStatus.ok:
        for transcription_obj in transcription.data:
            if transcription_obj["author"] == volunteer["username"]:
                logger.info("Found a matching transcription for that post!")
                return transcription_obj

    logger.info(f"creating transcription {post['id']}")
    blossom.create_transcription(
        transcription_id=t_comment.id,
        text=comment_body,
        url=f"https://reddit.com{t_comment.permalink}",
        username=volunteer["username"],
        submission_id=post["id"],
        removed_from_reddit=False,
    )
    if transcribot_comment:
        logger.info(f"creating OCR transcription on {post.id}")
        blossom.create_transcription(
            transcription_id=transcribot_comment.id,
            text=transcribot_text,
            url=f"https://reddit.com{transcribot_comment.permalink}",
            username="transcribot",
            submission_id=post["id"],
            removed_from_reddit=False,
        )


def get_or_create_post(tor_post, v):
    p = blossom.get_submission(original_id=tor_post.id)
    if p.status == BlossomStatus.ok:
        logger.info("Found a matching post for a transcription ID!")
        return p.data

    logger.info(f"creating post {tor_post.id}")

    try:
        image_url = REDDIT.submission(url=tor_post.url).url
    except (prawcore.exceptions.Forbidden, prawcore.exceptions.NotFound):
        image_url = None

    new_submission = blossom.create_submission(
        post_id=tor_post.id,
        post_url=f"https://reddit.com{tor_post.permalink}",
        original_url=tor_post.url,
        content_url=image_url,
    )
    blossom.claim(new_submission.data["id"], v["username"])
    blossom.done(new_submission.data["id"], v["username"], mod_override=True)
    return new_submission.data


def get_anon_user():
    return get_or_create_user("GrafeasAnonymousUser")


def generate_dummy_post(vlntr: Dict = None) -> None:
    logger.info(f"creating dummy post...")
    new_submission = blossom.create_submission(
        post_id=str(uuid.uuid4()),
        post_url="https://example.com",
        original_url="https://example.com",
        content_url="https://example.com",
    )
    if vlntr:
        blossom.claim(
            submission_id=new_submission.data["id"], username=vlntr["username"]
        )
        blossom.done(
            submission_id=new_submission.data["id"],
            username=vlntr["username"],
            mod_override=True,
        )
    return new_submission.data


def generate_dummy_transcription(vlntr: Dict, post: Dict = None):
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
    blossom.create_transcription(
        submission_id=post["id"],
        username=vlntr["username"],
        text="dummy transcription",
        url="https://example.com",
        transcription_id=str(uuid.uuid4()),
        removed_from_reddit=False,
    )
