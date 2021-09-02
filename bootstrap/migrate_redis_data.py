import json
import time
from datetime import datetime
from typing import Dict, List, Optional, TypedDict

from psaw import PushshiftAPI

from bootstrap import BATCH_SIZE, REDIS_DATA_PATH, USER_BLACKLIST, USER_WHITELIST

push = PushshiftAPI()

comment_filter = ["author", "body", "created_utc", "id", "link_id"]
submission_filter = ["created_utc", "id", "permalink", "title", "url"]


class CommentData(TypedDict):
    author: str
    body: str
    created_utc: datetime
    id: str
    link_id: str


class SubmissionData(TypedDict):
    created_utc: datetime
    id: str
    permalink: str
    title: str
    url: str


class RedditEntry(TypedDict):
    done_comment: Optional[CommentData]
    tor_submission: Optional[SubmissionData]
    partner_submission: Optional[SubmissionData]
    claim_comment: Optional[CommentData]
    ocr_transcriptions: Optional[List[CommentData]]
    transcriptions: Optional[List[CommentData]]


RedditData = Dict[str, RedditEntry]


class RedisEntry(TypedDict):
    username: str
    transcriptions: int
    posts_completed: List[str]


RedisData = Dict[str, RedisEntry]


def main():
    redis_data = get_redis_data()
    done_ids = []
    for user in redis_data:
        done_ids += redis_data[user]["posts_completed"]
    process_done_ids(done_ids)


def process_done_ids(done_ids: List[str]):
    all_start = time.time()
    cur_index = 0
    # Process the comments in batches (we merge some of the API calls)
    while cur_index < len(done_ids):
        print(f"====== {cur_index}/{len(done_ids)} ======")
        cur_batch = done_ids[cur_index : cur_index + BATCH_SIZE]
        start = time.time()
        process_done_batch(cur_batch)
        dur = time.time() - start
        avg_dur = dur / (min(len(done_ids), cur_index + BATCH_SIZE) - cur_index)
        print(f"Done in {dur:.2f} s ({avg_dur:.2f} s avg).")
        cur_index += BATCH_SIZE

    dur = time.time() - all_start
    print(f"====== {len(done_ids)}/{len(done_ids)} ======")
    print(f"DONE in {dur:.2f} s ({dur/len(done_ids):.2f} s avg).")


def get_redis_data() -> RedisData:
    """Get the Redis data to process."""
    with open(REDIS_DATA_PATH, "r") as redis_file:
        # Load the redis data
        redis_text = redis_file.read()
        redis_data: RedisData = json.loads(redis_text)

        # Filter the data
        if USER_WHITELIST is not None:
            redis_data = {k: v for k, v in redis_data.items() if k in USER_WHITELIST}
        if USER_BLACKLIST is not None:
            redis_data = {
                k: v for k, v in redis_data.items() if k not in USER_BLACKLIST
            }

        return redis_data


def process_done_batch(done_ids: List[str]):
    print(f"Processing {', '.join(done_ids)}")
    data: Dict[str, RedditEntry] = {}
    for done_id in done_ids:
        data[done_id] = {
            "done_comment": None,
            "tor_submission": None,
            "partner_submission": None,
            "claim_comment": None,
            "ocr_transcriptions": None,
            "transcriptions": None,
        }

    # First, do all the calls that we can do in batches
    fetch_done_comments(data)
    fetch_tor_submissions(data)
    fetch_partner_submissions(data)
    # Next we need to do the individual calls
    fetch_claim_comment(data)
    fetch_ocr_transcriptions(data)
    fetch_transcriptions(data)


def fetch_done_comments(data: RedditData) -> RedditData:
    print("Fetching done comments...", end=" ")
    start = time.time()
    done_ids = [done_id for done_id in data]
    done_comments = list(
        push.search_comments(ids=done_ids, limit=BATCH_SIZE, filter=comment_filter,)
    )
    done_comments = [dict_from_comment(done) for done in done_comments]

    for done_id in data:
        matching_comments = [done for done in done_comments if done["id"] == done_id]
        if len(matching_comments) > 0:
            data[done_id]["done_comment"] = matching_comments[0]

    dur = time.time() - start
    print(f"{len(done_comments)}/{len(done_ids)} found in {dur:.2f} s.")
    return data


def fetch_tor_submissions(data: RedditData) -> RedditData:
    print("Fetching ToR submissions...", end=" ")
    start = time.time()
    done_comments = [data[done_id]["done_comment"] for done_id in data]
    tor_submission_ids = [done["link_id"] for done in done_comments if done is not None]
    tor_submissions = list(
        push.search_submissions(
            ids=tor_submission_ids, limit=BATCH_SIZE, filter=submission_filter,
        )
    )
    tor_submissions = [dict_from_submission(tor_sub) for tor_sub in tor_submissions]
    for done_id in data:
        done = data[done_id]["done_comment"]
        if done is None:
            continue
        matching_subs = [
            tor_sub
            for tor_sub in tor_submissions
            if tor_sub["id"] == done["link_id"][3:]
        ]
        if len(matching_subs) > 0:
            data[done_id]["tor_submission"] = matching_subs[0]

    dur = time.time() - start
    print(f"{len(tor_submissions)}/{len(tor_submission_ids)} found in {dur:.2f} s.")
    return data


def fetch_partner_submissions(data: RedditData) -> RedditData:
    print("Fetching partner submissions...", end=" ")
    start = time.time()
    partner_submissions = [data[done_id]["tor_submission"] for done_id in data]
    partner_submission_urls = [
        sub["url"] for sub in partner_submissions if sub is not None
    ]
    partner_submission_ids = [
        extract_submission_id_from_url(url) for url in partner_submission_urls
    ]
    partner_submissions = list(
        push.search_submissions(
            ids=partner_submission_ids, limit=BATCH_SIZE, filter=submission_filter,
        )
    )
    partner_submissions = [
        dict_from_submission(partner_sub) for partner_sub in partner_submissions
    ]
    for done_id in data:
        tor_sub = data[done_id]["tor_submission"]
        if tor_sub is None:
            continue
        matching_subs = [
            p_sub
            for p_sub in partner_submissions
            if p_sub["id"] == extract_submission_id_from_url(tor_sub["url"])
        ]
        if len(matching_subs) > 0:
            data[done_id]["partner_submission"] = matching_subs[0]

    dur = time.time() - start
    print(
        f"{len(partner_submissions)}/{len(partner_submission_ids)} found in {dur:.2f} s."
    )
    return data


def fetch_claim_comment(data: RedditData) -> RedditData:
    print("Fetching claim comment...", end=" ")
    start = time.time()
    found_count = 0
    not_found_count = 0
    for done_id in data:
        done = data[done_id]["done_comment"]
        if done is None:
            continue
        claim_comments = list(
            push.search_comments(
                link_id=done["link_id"],
                author=done["author"],
                q="claim",
                limit=1,
                filter=comment_filter,
            )
        )
        claim_comments = [dict_from_comment(claim) for claim in claim_comments]
        if len(claim_comments) > 0:
            data[done_id]["claim_comment"] = claim_comments[0]
            found_count += 1
        else:
            not_found_count += 1

    dur = time.time() - start
    print(f"{found_count}/{found_count + not_found_count} found in {dur:.2f} s.")
    return data


def fetch_ocr_transcriptions(data: RedditData) -> RedditData:
    print("Fetching OCR transcriptions...", end=" ")
    start = time.time()
    found_count = 0
    not_found_count = 0
    for done_id in data:
        done = data[done_id]["done_comment"]
        if done is None:
            continue
        ocr_transcriptions = list(
            push.search_comments(
                link_id=done["link_id"],
                author="transcribot",
                q='-"It looks like there\'s text in this image."',
                filter=comment_filter,
            )
        )
        ocr_transcriptions = [dict_from_comment(ocr) for ocr in ocr_transcriptions]
        if len(ocr_transcriptions) > 0:
            data[done_id]["ocr_transcriptions"] = ocr_transcriptions
            found_count += 1
        else:
            not_found_count += 1

    dur = time.time() - start
    print(f"{found_count}/{found_count + not_found_count} found in {dur:.2f} s.")
    return data


def fetch_transcriptions(data: RedditData) -> RedditData:
    print("Fetching transcriptions...", end=" ")
    start = time.time()
    found_count = 0
    not_found_count = 0
    for done_id in data:
        done = data[done_id]["done_comment"]
        p_sub = data[done_id]["partner_submission"]
        if done is None or p_sub is None:
            continue
        transcriptions = list(
            push.search_comments(
                link_id=p_sub["id"], author=done["author"], filter=comment_filter,
            )
        )
        transcriptions = [dict_from_comment(tr) for tr in transcriptions]
        if len(transcriptions) > 0:
            data[done_id]["transcriptions"] = transcriptions
            found_count += 1
        else:
            not_found_count += 1

    dur = time.time() - start
    print(f"{found_count}/{found_count + not_found_count} found in {dur:.2f} s.")
    return data


def dict_from_comment(comment) -> CommentData:
    return {
        "author": comment[0],
        "body": comment[1],
        "created_utc": datetime.utcfromtimestamp(comment[2]),
        "id": comment[3],
        "link_id": comment[4],
    }


def dict_from_submission(submission) -> SubmissionData:
    return {
        "created_utc": datetime.utcfromtimestamp(submission[0]),
        "id": submission[1],
        "permalink": submission[2],
        "title": submission[3],
        "url": submission[4],
    }


def extract_submission_id_from_url(url: str) -> str:
    """Extracts the Reddit ID from a submission URL.
    An URL looks like this:
    https://reddit.com/r/CuratedTumblr/comments/nybt3m/medieval_medicines_and_superbugs/
    The ID of this URL would be "nybt3m".
    """
    return url.split("/")[6]


main()
