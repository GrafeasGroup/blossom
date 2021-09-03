import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, TypedDict, Union

from blossom_wrapper import BlossomStatus
from psaw import PushshiftAPI

from bootstrap import (
    BATCH_SIZE,
    REDIS_DATA_PATH,
    USER_BLACKLIST,
    USER_WHITELIST,
    blossom,
)

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
    username: str
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

# A tuple of username and done ID
DoneData = Tuple[str, str]


def main():
    redis_data = get_redis_data()
    done_data: List[DoneData] = []
    for user in redis_data:
        done_data += [
            (user, done_id) for done_id in redis_data[user]["posts_completed"]
        ]
    process_done_ids(done_data)


def process_done_ids(done_data: List[DoneData]):
    """Process the list of IDs saved in Redis.

    Every ID belongs to a Reddit "done" comment.
    """
    all_start = time.time()
    cur_index = 0
    # Process the comments in batches (we merge some of the API calls)
    while cur_index < len(done_data):
        print(f"====== {cur_index}/{len(done_data)} ======")
        cur_batch = done_data[cur_index : cur_index + BATCH_SIZE]
        start = time.time()
        process_done_batch(cur_batch)
        dur = time.time() - start
        avg_dur = dur / (min(len(done_data), cur_index + BATCH_SIZE) - cur_index)
        print(f"Done in {dur:.2f} s ({avg_dur:.2f} s avg).")
        cur_index += BATCH_SIZE

    dur = time.time() - all_start
    print(f"====== {len(done_data)}/{len(done_data)} ======")
    print(f"DONE in {dur:.2f} s ({dur/len(done_data):.2f} s avg).")


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


def process_done_batch(done_data: List[DoneData]):
    """Process a batch of IDs saved in Redis.

    Every ID is the Reddit ID of a "done" comment.
    """
    done_data = filter_processed_ids(done_data)
    data: Dict[str, RedditEntry] = {}
    for username, done_id in done_data:
        data[done_id] = {
            "username": username,
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


def filter_processed_ids(done_data: List[DoneData]) -> List[DoneData]:
    """Filters out the IDs that have already been processed before.

    This can be determined by checking if a submission already has
    the ID as redis_id attribute in Blossom.
    """
    print("Skipping processed IDs...", end=" ")
    start = time.time()
    filtered_ids: List[DoneData] = []
    for username, done_id in done_data:
        response = blossom.get_submission(redis_id=done_id)
        if response.status == BlossomStatus.not_found:
            filtered_ids.append((username, done_id))

    dur = time.time() - start
    print(f"{len(filtered_ids)}/{len(done_data)} need processing in {dur:.2f} s.")
    return filtered_ids


def submit_data(data: RedditData):
    """Submit the fetched data to Blossom."""
    pass


BlossomSubmission = Dict[str, Union[str, bool, int]]


def get_dummy_submissions(author: str, count: int) -> List[BlossomSubmission]:
    """Get the given number of dummy submissions for the given author."""
    # Get the author ID
    author_response = blossom.get_user(author)
    if author_response.status != BlossomStatus.ok:
        return []
    author_id = author_response.data["id"]

    # Get dummy submissions from the author
    example_url = "https://example.com"
    dummy_response = blossom.get_submission(
        completed_by=author_id,
        url=example_url,
        tor_url=example_url,
        content_url=example_url,
        page_size=count,
    )
    if dummy_response.status != BlossomStatus.ok:
        return []
    return dummy_response.data


def fetch_done_comments(data: RedditData) -> RedditData:
    """Fetch the done comment from Pushshift.

    We can fetch multiple comments at the same time.
    Example:
    https://api.pushshift.io/reddit/comment/search?ids=h1jacqk&fields=author,body,link_id,created_utc
    """
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
    """Fetch the ToR submission from Pushshift.

    We can fetch multiple submissions at the same time.
    Example:
    https://api.pushshift.io/reddit/submission/search?ids=t3_nybvr3&fields=id,url,created_utc,permalink
    """
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
    """Fetches the partner submission from Pushshift.

    We can fetch multiple submissions at the same time.
    Example:
    https://api.pushshift.io/reddit/submission/search?ids=nybt3m&fields=id,url,title,created_utc,permalink
    """
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
    """Fetch the claim comment from Pushshift.

    A claim comment is a comment made on the ToR submission by the author of the done
    and contains the phrase "claim".
    Example:
    https://api.pushshift.io/reddit/comment/search?link_id=t3_nybvr3&author=Tim3303&fields=author,body,link_id,created_utc&q=claim
    """
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
    """Fetch the OCR transcription from Pushshift.

    An OCR transcription is a comment on the ToR submission which is made by u/transcribot
    and doesn't contain the phrase "It looks like there's text in this image".
    Example:
    https://api.pushshift.io/reddit/comment/search?link_id=t3_nybvr3&author=transcribot&fields=author,body,link_id,created_utc&q=-%22It%20looks%20like%20there%27s%20text%20in%20this%20image.%22
    """
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
    """Fetch the transcription comments from Pushshift.

    Transcription comments are comments made on the partner submission by the
    author of the done comment. They have to contain the link to the ToR FAQ.
    Example:
    https://api.pushshift.io/reddit/comment/search?link_id=nybt3m&author=Tim3303&fields=author,body,link_id,created_utc&q=https://www.reddit.com/r/TranscribersOfReddit/wiki
    """
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
    """Convert the Pushshift data of a comment to a dict.

    We get a tuple-like struct with the keys of the fields sorted alphabetically.
    There is probably an easier way to access the data, but the documentation
    is minimal.
    """
    return {
        "author": comment[0],
        "body": comment[1],
        "created_utc": datetime.utcfromtimestamp(comment[2]),
        "id": comment[3],
        "link_id": comment[4],
    }


def dict_from_submission(submission) -> SubmissionData:
    """Convert the Pushshift data of a submission to a dict.

    We get a tuple-like struct with the keys of the fields sorted alphabetically.
    There is probably an easier way to access the data, but the documentation
    is minimal.
    """
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
