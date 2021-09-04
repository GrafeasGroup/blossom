import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, TypedDict, Union

from blossom_wrapper import BlossomStatus
from psaw import PushshiftAPI

from bootstrap import (
    BATCH_SIZE,
    CACHE_DATA_PATH,
    INCOMPLETE_DATA_PATH,
    REDIS_DATA_PATH,
    USER_BLACKLIST,
    USER_WHITELIST,
    blossom,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)

push = PushshiftAPI()

comment_filter = ["author", "body", "created_utc", "id", "link_id", "permalink"]
submission_filter = ["created_utc", "id", "permalink", "title", "url"]


class CommentData(TypedDict):
    author: str
    body: str
    created_utc: datetime
    id: str
    link_id: str
    permalink: str


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
    submission_saved: Optional[bool]
    transcription_saved: Optional[bool]
    ocr_saved: Optional[bool]


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
        logging.info(f"====== {cur_index}/{len(done_data)} ======")
        cur_batch = done_data[cur_index : cur_index + BATCH_SIZE]
        start = time.time()
        process_done_batch(cur_batch)
        dur = time.time() - start
        avg_dur = dur / (min(len(done_data), cur_index + BATCH_SIZE) - cur_index)
        logging.info(f"Done in {dur:.2f} s ({avg_dur:.2f} s avg).")
        cur_index += BATCH_SIZE

    dur = time.time() - all_start
    logging.info(f"====== {len(done_data)}/{len(done_data)} ======")
    logging.info(f"DONE in {dur:.2f} s ({dur/len(done_data):.2f} s avg).")


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
    done_data = filter_cached_ids(done_data)
    done_data = filter_processed_ids(done_data)

    data: Dict[str, RedditEntry] = {}
    for username, done_id in done_data:
        default_entry: RedditEntry = {
            "username": username,
            "done_comment": None,
            "tor_submission": None,
            "partner_submission": None,
            "claim_comment": None,
            "ocr_transcriptions": None,
            "transcriptions": None,
            "submission_saved": False,
            "transcription_saved": False,
            "ocr_saved": False,
        }
        data[done_id] = default_entry

    # First, do all the calls that we can do in batches
    fetch_done_comments(data)
    fetch_tor_submissions(data)
    fetch_partner_submissions(data)
    # Next we need to do the individual calls
    fetch_claim_comment(data)
    fetch_ocr_transcriptions(data)
    fetch_transcriptions(data)
    # Submit the data to Blossom
    submit_data_to_blossom(data)
    # Cache data
    cache_entries(data)
    save_incomplete_entries(data)


def filter_cached_ids(done_data: List[DoneData]) -> List[DoneData]:
    """Filters out the IDs that have already been cached."""
    start = time.time()
    filtered_ids: List[DoneData] = []
    cache = get_data_file_dict(CACHE_DATA_PATH)
    for username, done_id in done_data:
        if username not in cache or done_id not in cache[username]:
            filtered_ids.append((username, done_id))

    dur = time.time() - start
    logging.info(
        f"Checked cache, {len(filtered_ids)}/{len(done_data)} need processing in {dur:.2f} s."
    )
    return filtered_ids


def filter_processed_ids(done_data: List[DoneData]) -> List[DoneData]:
    """Filters out the IDs that have already been processed before.

    This can be determined by checking if a submission already has
    the ID as redis_id attribute in Blossom.
    """
    start = time.time()
    filtered_ids: List[DoneData] = []
    for username, done_id in done_data:
        response = blossom.get_submission(redis_id=done_id)
        if response.status == BlossomStatus.not_found:
            filtered_ids.append((username, done_id))

    dur = time.time() - start
    logging.info(
        f"Checked Blossom, {len(filtered_ids)}/{len(done_data)} need processing in {dur:.2f} s."
    )
    return filtered_ids


def submit_data_to_blossom(data: RedditData) -> RedditData:
    """Submit the fetched data to Blossom."""
    grouped_data = group_data_by_author(data)
    for username in grouped_data:
        start = time.time()
        user_data = grouped_data[username]
        user_data_list = [v for k, v in user_data.items()]
        dummy_subs = get_dummy_submissions(username, len(user_data))
        for blossom_submission, entry in zip(dummy_subs, user_data_list):
            new_entry = submit_entry_to_blossom(blossom_submission, entry)
            data[entry["done_comment"]["id"]] = new_entry

        dur = time.time() - start
        logging.info(
            f"Submitting data for {username} {len(dummy_subs)}/{len(user_data_list)} dummy submissions patched {dur:.2f} s."
        )

    return data


def get_data_file_dict(file_path: str) -> Dict:
    """Get the dict stored in a data file."""
    if not os.path.exists(file_path):
        # Create the file if it doesn't exist
        open(file_path, "w")

    with open(file_path, "r") as f:
        content = f.read()
        if content.strip() == "":
            content = "{}"
        return json.loads(content)


def cache_entries(data: RedditData):
    """Cache the entries so that they don't need to be fetched again."""
    cur_cache = get_data_file_dict(CACHE_DATA_PATH)

    for done_id, entry in data.items():
        username = entry["username"]

        if username not in cur_cache:
            cur_cache[username] = []

        cur_entries = cur_cache[username]
        cur_entries.append(done_id)
        cur_cache[username] = cur_entries

    with open(CACHE_DATA_PATH, "w") as f:
        f.write(json.dumps(cur_cache, indent=2))


def save_incomplete_entries(data: RedditData):
    """Save all entries that we couldn't get all data for."""
    cur_cache = get_data_file_dict(INCOMPLETE_DATA_PATH)

    for done_id, entry in data.items():
        if not should_be_saved(entry):
            continue

        username = entry["username"]

        if username not in cur_cache:
            cur_cache[username] = {}

        cur_cache[username][done_id] = get_incomplete_data_dict(entry)

    with open(INCOMPLETE_DATA_PATH, "w") as f:
        f.write(json.dumps(cur_cache, indent=2))


def should_be_saved(entry: RedditEntry) -> bool:
    return (
        entry["done_comment"] is None
        or entry["claim_comment"] is None
        or entry["tor_submission"] is None
        or entry["partner_submission"] is None
        or entry["transcriptions"] is None
        or len(entry["transcriptions"]) == 0
        or entry["submission_saved"] is False
        or entry["transcription_saved"] is False
        or entry["ocr_saved"] is False
    )


def get_incomplete_data_dict(entry: RedditEntry) -> Dict:
    """Get a dict from the entry that can be saved to a JSON file."""
    data_dict = {
        "done_comment": entry["done_comment"]["id"] if entry["done_comment"] else None,
        "claim_comment": entry["claim_comment"]["id"]
        if entry["claim_comment"]
        else None,
        "tor_submission": entry["tor_submission"]["id"]
        if entry["tor_submission"]
        else None,
        "partner_submission": entry["partner_submission"]["id"]
        if entry["partner_submission"]
        else None,
        "transcriptions": [tr["id"] for tr in entry["transcriptions"]]
        if entry["transcriptions"] and len(entry["transcriptions"]) > 0
        else None,
        "ocr_transcriptions": [ocr["id"] for ocr in entry["ocr_transcriptions"]]
        if entry["ocr_transcriptions"] and len(entry["ocr_transcriptions"]) > 0
        else None,
        "submission_saved": entry["submission_saved"],
        "transcription_saved": entry["transcription_saved"],
        "ocr_saved": entry["ocr_saved"],
    }
    # Delete None entries
    return {k: v for k, v in data_dict.items() if v is not None}


def extract_title_from_tor_title(tor_title: str) -> Optional[str]:
    """Extract the submission title from the title of the ToR submission.

    Example of a ToR title:
        AreTheStraightsOK | Image | "This straight dude is not okay / found on fb"
    The submission title would be the following:
        This straight dude is not okay / found on fb
    """
    parts = tor_title.split("|")
    if len(parts) != 3:
        return None
    # Remove spaces and the quotation marks
    return parts[2].strip(' "')


def submit_entry_to_blossom(
    blossom_submission: Dict, entry: RedditEntry
) -> RedditEntry:
    """Submit a single data entry to Blossom."""
    blossom_id = blossom_submission["id"]

    claim = entry["claim_comment"]
    done = entry["done_comment"]
    tor_sub = entry["tor_submission"]
    partner_sub = entry["partner_submission"]
    transcriptions = entry["transcriptions"]
    ocr_transcriptions = entry["ocr_transcriptions"]

    if done is None:
        # There is nothing to submit
        entry["submission_saved"] = None
        entry["transcription_saved"] = None
        entry["ocr_saved"] = None
        return entry

    # Assemble all the data that we could get
    original_id = (
        partner_sub["id"]
        if partner_sub
        else extract_id_from_reddit_url(tor_sub["url"])
        if tor_sub
        else None
    )
    create_time = (
        partner_sub["created_utc"]
        if partner_sub
        else tor_sub["created_utc"]
        if tor_sub
        else done["created_utc"]
    )
    title = (
        partner_sub["title"]
        if partner_sub
        else extract_title_from_tor_title(tor_sub["title"])
        if tor_sub
        else None
    )
    claim_time = claim["created_utc"] if claim else done["created_utc"]
    complete_time = done["created_utc"]
    url = "https://reddit.com/" + partner_sub["permalink"] if partner_sub else None
    tor_url = "https://reddit.com/" + tor_sub["permalink"] if tor_sub else None
    content_url = partner_sub["url"] if partner_sub else None
    archived = True
    cannot_ocr = ocr_transcriptions is None or len(ocr_transcriptions) == 0
    redis_id = done["id"]

    sub_response = blossom.patch(
        f"submission/{blossom_id}",
        {
            "original_id": original_id,
            "create_time": create_time.isoformat(),
            "claim_time": claim_time.isoformat(),
            "complete_time": complete_time.isoformat(),
            "url": url,
            "title": title,
            "tor_url": tor_url,
            "content_url": content_url,
            "archived": archived,
            "cannot_ocr": cannot_ocr,
            "redis_id": redis_id,
        },
    )
    if sub_response.ok:
        entry["submission_saved"] = True
    else:
        logging.warning(
            "Failed to patch submission %s of done %s to Blossom!",
            original_id,
            done["id"],
        )

    if transcriptions and len(transcriptions) > 0:
        # Patch/Create the transcription too
        transcription_text = "\n\n".join([tr["body"] for tr in transcriptions])

        ocr_data = {
            "author": entry["username"],
            "submission": blossom_id,
            "create_time": transcriptions[0]["created_utc"].isoformat(),
            "original_id": transcriptions[0]["id"],
            "url": "https://reddit.com/" + transcriptions[0]["permalink"],
            "text": transcription_text,
            "removed_from_reddit": False,
        }

        if len(blossom_submission["transcription_set"]) > 0:
            # We already have a dummy transcription, patch it
            transcription_id = extract_id_from_grafeas_url(
                blossom_submission["transcription_set"][0]
            )
            tr_response = blossom.patch(
                f"transcription/{transcription_id}", data=ocr_data
            )
            if tr_response.ok:
                entry["transcription_saved"] = True
            else:
                logging.warning(
                    "Failed to patch transcription %s of done %s to Blossom!",
                    transcriptions[0]["id"],
                    done["id"],
                )
        else:
            # No transcription yet, create a new one
            tr_response = blossom.post("transcription", data=ocr_data)
            if tr_response.ok:
                entry["transcription_saved"] = True
            else:
                logging.warning(
                    "Failed to create transcription %s of done %s to Blossom!",
                    transcriptions[0]["id"],
                    done["id"],
                )
    else:
        # There is no transcription to save
        entry["transcription_saved"] = None

    if ocr_transcriptions and len(ocr_transcriptions) > 0:
        # Create the OCR transcription too
        ocr_text = "\n\n".join([ocr["body"] for ocr in ocr_transcriptions])

        ocr_data = {
            "submission": blossom_id,
            "create_time": ocr_transcriptions[0]["created_utc"].isoformat(),
            "original_id": ocr_transcriptions[0]["id"],
            "url": "https://reddit.com/" + ocr_transcriptions[0]["permalink"],
            "text": ocr_text,
            "removed_from_reddit": False,
        }

        ocr_response = blossom.post("transcription", data=ocr_data)
        if ocr_response.ok:
            entry["ocr_saved"] = True
        else:
            logging.warning(
                "Failed to create OCR %s of done %s to Blossom!",
                ocr_transcriptions[0]["id"],
                done["id"],
            )
    else:
        # There is no OCR to save
        entry["ocr_saved"] = None

    return entry


GroupedRedditData = Dict[str, RedditData]


def group_data_by_author(data: RedditData) -> GroupedRedditData:
    """Group the reddit data by author."""
    grouped_data: GroupedRedditData = {}
    for done_id in data:
        entry = data[done_id]
        username = entry["username"]
        if username not in grouped_data:
            grouped_data[username] = {}
        grouped_data[username][done_id] = entry
    return grouped_data


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
    logging.info(
        f"Fetched done comments {len(done_comments)}/{len(done_ids)} found in {dur:.2f} s."
    )
    return data


def fetch_tor_submissions(data: RedditData) -> RedditData:
    """Fetch the ToR submission from Pushshift.

    We can fetch multiple submissions at the same time.
    Example:
    https://api.pushshift.io/reddit/submission/search?ids=t3_nybvr3&fields=id,url,created_utc,permalink
    """
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
    logging.info(
        f"Fetched ToR submissions {len(tor_submissions)}/{len(tor_submission_ids)} found in {dur:.2f} s."
    )
    return data


def fetch_partner_submissions(data: RedditData) -> RedditData:
    """Fetches the partner submission from Pushshift.

    We can fetch multiple submissions at the same time.
    Example:
    https://api.pushshift.io/reddit/submission/search?ids=nybt3m&fields=id,url,title,created_utc,permalink
    """
    start = time.time()
    partner_submissions = [data[done_id]["tor_submission"] for done_id in data]
    partner_submission_urls = [
        sub["url"] for sub in partner_submissions if sub is not None
    ]
    partner_submission_ids = [
        extract_id_from_reddit_url(url) for url in partner_submission_urls
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
            if p_sub["id"] == extract_id_from_reddit_url(tor_sub["url"])
        ]
        if len(matching_subs) > 0:
            data[done_id]["partner_submission"] = matching_subs[0]

    dur = time.time() - start
    logging.info(
        f"Fetched partner submissions {len(partner_submissions)}/{len(partner_submission_ids)} found in {dur:.2f} s."
    )
    return data


def fetch_claim_comment(data: RedditData) -> RedditData:
    """Fetch the claim comment from Pushshift.

    A claim comment is a comment made on the ToR submission by the author of the done
    and contains the phrase "claim".
    Example:
    https://api.pushshift.io/reddit/comment/search?link_id=t3_nybvr3&author=Tim3303&fields=author,body,link_id,created_utc&q=claim
    """
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
    logging.info(
        f"Fetched claim comment {found_count}/{found_count + not_found_count} found in {dur:.2f} s."
    )
    return data


def fetch_ocr_transcriptions(data: RedditData) -> RedditData:
    """Fetch the OCR transcription from Pushshift.

    An OCR transcription is a comment on the ToR submission which is made by u/transcribot
    and doesn't contain the phrase "It looks like there's text in this image".
    Example:
    https://api.pushshift.io/reddit/comment/search?link_id=t3_nybvr3&author=transcribot&fields=author,body,link_id,created_utc&q=-%22It%20looks%20like%20there%27s%20text%20in%20this%20image.%22
    """
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
    logging.info(
        f"Fetched OCR transcriptions {found_count}/{found_count + not_found_count} found in {dur:.2f} s."
    )
    return data


def fetch_transcriptions(data: RedditData) -> RedditData:
    """Fetch the transcription comments from Pushshift.

    Transcription comments are comments made on the partner submission by the
    author of the done comment. They have to contain the link to the ToR FAQ.
    Example:
    https://api.pushshift.io/reddit/comment/search?link_id=nybt3m&author=Tim3303&fields=author,body,link_id,created_utc&q=https://www.reddit.com/r/TranscribersOfReddit/wiki
    """
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
    logging.info(
        f"Fetched transcriptions {found_count}/{found_count + not_found_count} found in {dur:.2f} s."
    )
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
        "permalink": comment[5],
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


def extract_id_from_grafeas_url(url: str) -> str:
    """Extract the ID from a Grafeas URL.

    An URL looks like this:
    https://grafeas.org/api/transcription/1957/
    This ID of this URL would be 1957.
    """
    return url.split("/")[-2]


def extract_id_from_reddit_url(url: str) -> str:
    """Extract the Reddit ID from a submission URL.

    An URL looks like this:
    https://reddit.com/r/CuratedTumblr/comments/nybt3m/medieval_medicines_and_superbugs/
    The ID of this URL would be "nybt3m".
    """
    return url.split("/")[6]


main()
