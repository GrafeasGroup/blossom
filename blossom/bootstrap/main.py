import logging
import sys
from datetime import datetime
from typing import Dict

from blossom_wrapper import BlossomStatus

from blossom.bootstrap import blossom
from blossom.bootstrap.db import (
    generate_dummy_post,
    generate_dummy_transcription,
    get_anon_user,
    get_or_create_post,
    get_or_create_transcription,
    get_or_create_user,
)
from blossom.bootstrap.helpers import (
    get_user_list_from_redis,
    graceful_interrupt_handler,
    pull_user_data_from_redis,
    redis,
)
from blossom.bootstrap.pushshift import (
    get_extended_transcript_body,
    get_tor_claim_and_done_from_pushshift,
    get_transcription_data_from_pushshift,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BootstrapException(Exception):
    pass


def yeet_user(redis_user_obj: Dict) -> None:
    r_username = redis_user_obj.get("username")
    r_gamma = redis_user_obj.get("transcriptions", 0)

    logger.info(f"Processing username: {r_username}")

    v = get_or_create_user(r_username).data
    if r_gamma > v["gamma"]:
        logger.warning(
            f"Missing dummy entries. Redis: {r_gamma} | Blossom: {v['gamma']}"
        )
        for _ in range(r_gamma - v["gamma"]):
            generate_dummy_post(v)

    v = get_or_create_user(r_username).data
    if r_gamma < v["gamma"]:
        logger.warning(f"Found discrepancy. Redis: {r_gamma} | Blossom: {v['gamma']}")
        response = blossom.post(
            "submission/yeet/",
            data={"username": r_username, "count": abs(r_gamma - v["gamma"])},
        )
        if response.status_code != 200:
            logger.error(f"Received a {response.status_code} - {response.json()}")
        else:
            logger.info(response.json())


def process_user(redis_user_obj: Dict):
    r_username = redis_user_obj.get("username")
    r_gamma = redis_user_obj.get("transcriptions", 0)
    r_transcriptions = redis_user_obj.get("posts_completed")

    logger.info(f"Processing username: {r_username}")

    v = get_or_create_user(r_username).data

    if r_gamma == 0:
        logger.info("No transcriptions listed for user. Continuing.")
        return

    if r_transcriptions is None:
        r_transcriptions = list()

    total_transcriptions_for_user = v["gamma"]
    # after all, they might have made new transcriptions since this version of the
    # db was pulled
    if total_transcriptions_for_user >= r_gamma:
        logger.info(
            "All the transcriptions for this user appear to be here. Moving on!"
        )
        return

    logger.debug(
        f"Gamma listed at {r_gamma}, found {len(r_transcriptions)} posts on record."
    )
    if r_gamma - len(r_transcriptions) != 0:
        logger.debug(
            f"Should generate {r_gamma - len(r_transcriptions)} dummy entries."
        )

    for t in r_transcriptions:
        start_time = datetime.now()
        try:
            # if this succeeds, then we don't need to worry about creating
            # everything and can just move on.
            submission = blossom.get_submission(redis_id=t)
            if submission.status == BlossomStatus.ok:
                submission = submission.data[0]
            else:
                raise BootstrapException

            transcription_resp = blossom.get_transcription(submission=submission["id"])
            if transcription_resp.status == BlossomStatus.ok:
                # we might get more than one transcription. Let's find the right one.
                proper_t = None
                for transcription_obj in transcription_resp.data:
                    if transcription_obj["author"] == submission["completed_by"]:
                        proper_t = transcription_obj
                if not proper_t:
                    logger.debug(
                        "Cannot find transcription by {r_username} on {t} -- creating!"
                    )
                else:
                    logger.debug(
                        "Success! Found existing transcription! Continuing on!"
                    )
                    continue
            else:
                raise BootstrapException

        except BootstrapException:
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
                p = get_or_create_post(tor_post, v)
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
                    generate_dummy_transcription(v, p)
            else:
                # I dunno what happened because pushshift should still have it.
                # Nonetheless, let's create a dummy transcription
                generate_dummy_transcription(v, p)
        end_time = datetime.now()
        logger.info(f"Completed operation in {(end_time - start_time).seconds} seconds")

    logged_transcription_count = get_or_create_user(r_username).data["gamma"]
    if logged_transcription_count < r_gamma:
        discrepancy_count = r_gamma - logged_transcription_count

        for _ in range(discrepancy_count):
            logger.info(f"Updating discrepancy count: {discrepancy_count}")
            generate_dummy_transcription(v)
        logger.info(f"Created {discrepancy_count} dummy transcriptions.")


def bootstrap(users):
    for z in users:
        with graceful_interrupt_handler() as handler:
            # process_user(z)
            yeet_user(z)
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

    logger.info(f"Creating at least {len(user_objects) * 2 + total_count} models...")
    get_anon_user()  # just make sure it exists
    # v_count = BlossomUser.objects.count()
    #     logger.info(
    #         f'{v_count} volunteers processed so far - {int((v_count / rconn.scard("accepted_CoC"))*100)}% of total.'
    #     )
    bootstrap(user_objects)


#
#     logger.info(f"Final count per Redis: {total_count}")
#     total_db_count = Transcription.objects.all().count()
#     logger.info(f"Final count per DB: {total_db_count}")


BOOTSTRAP_THAT_MOFO()
