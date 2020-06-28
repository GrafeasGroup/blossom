import gc
import logging
import sys
from datetime import datetime
from typing import Dict

from django.db import reset_queries

from api.bootstrap.db import (
    get_or_create_user,
    get_anon_user,
    get_or_create_post,
    get_or_create_transcription,
    generate_dummy_transcription,
    generate_dummy_post,
)
from api.bootstrap.helpers import (
    get_user_list_from_redis,
    pull_user_data_from_redis,
    redis,
    graceful_interrupt_handler,
)
from api.bootstrap.pushshift import (
    get_tor_claim_and_done_from_pushshift,
    get_extended_transcript_body,
    get_transcription_data_from_pushshift,
)
from api.models import Transcription
from authentication.models import BlossomUser

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def process_user(redis_user_obj: Dict):
    username = redis_user_obj.get("username")
    gamma = redis_user_obj.get("transcriptions", 0)
    transcriptions = redis_user_obj.get("posts_completed")

    logger.info(f"Processing username: {username}")

    v = get_or_create_user(username)

    if gamma == 0:
        logger.info("No transcriptions listed for user. Continuing.")
        return

    if transcriptions is None:
        transcriptions = list()

    total_transcriptions_for_user = Transcription.objects.filter(author=v).count()
    # after all, they might have made new transcriptions since this version of the
    # db was pulled
    if total_transcriptions_for_user >= gamma:
        logger.info(
            "All the transcriptions for this user appear to be here. Moving on!"
        )
        return

    logger.debug(
        f"Gamma listed at {gamma}, found {len(transcriptions)} posts on record."
    )
    if gamma - len(transcriptions) != 0:
        logger.debug(f"Should generate {gamma - len(transcriptions)} dummy entries.")

    for t in transcriptions:
        start_time = datetime.now()
        try:
            # if this succeeds, then we don't need to worry about creating
            # everything and can just move on.
            Transcription.objects.get(submission__redis_id=t)
            logger.debug("Success! Found existing transcription! Continuing on!")
            continue
        except Transcription.DoesNotExist:
            logger.debug(f"Processing {t}")
            # t_comment is the comment that holds the transcription
            (
                tor_post,
                t_comment,
                post_id,
                all_comments,
            ) = get_transcription_data_from_pushshift(t)
            (
                claim,
                done,
                transcribot_text,
                transcribot_comment,
            ) = get_tor_claim_and_done_from_pushshift(tor_post)
            if tor_post is not None:
                p = get_or_create_post(tor_post, v, claim, done, t)
            else:
                logger.error("tor_post returned None. Using dummy post.")
                p = generate_dummy_post(v)

            if t_comment is not None:
                try:
                    # this is really where we should end up all the time
                    t_comment_body = get_extended_transcript_body(
                        t_comment, post_id, all_comments
                    )
                    get_or_create_transcription(
                        p,
                        v,
                        t_comment,
                        t_comment_body,
                        transcribot_text,
                        transcribot_comment,
                    )
                except (MemoryError, StopIteration):
                    # this happens too often. Maybe we can control it?
                    gc.collect()
                    generate_dummy_transcription(v, p)
            else:
                # I dunno what happened because pushshift should still have it.
                # Nonetheless, let's create a dummy transcription
                generate_dummy_transcription(v, p)
        end_time = datetime.now()
        reset_queries()
        logger.info(f"Completed operation in {(end_time - start_time).seconds} seconds")

    logged_transcription_count = Transcription.objects.filter(author=v).count()
    if logged_transcription_count < gamma:
        discrepancy_count = gamma - logged_transcription_count

        for _ in range(discrepancy_count):
            generate_dummy_transcription(v)
        logger.info(f"Created {discrepancy_count} dummy transcriptions.")


def bootstrap(users):
    for z in users:
        with graceful_interrupt_handler() as handler:
            gc.collect()
            process_user(z)
            if handler.interrupted:
                sys.exit()


def BOOTSTRAP_THAT_MOFO():
    logger.critical("BOOTSTRAPPING THAT MOFO")
    rconn = redis()

    logger.info("Getting user data from Redis...")
    user_list = get_user_list_from_redis(rconn)

    logger.info("Parsing user data from Redis...")
    user_objects = pull_user_data_from_redis(user_list, rconn)

    total_count = int(rconn.get("total_completed"))

    logger.info(f"Creating at least {len(user_objects)*2 + total_count} models...")
    get_anon_user()  # just make sure it exists
    v_count = BlossomUser.objects.count()
    logger.info(
        f'{v_count} volunteers processed so far - {int((v_count / rconn.scard("accepted_CoC"))*100)}% of total.'
    )
    bootstrap(user_objects)

    logger.info(f"Final count per Redis: {total_count}")
    total_db_count = Transcription.objects.all().count()
    logger.info(f"Final count per DB: {total_db_count}")
