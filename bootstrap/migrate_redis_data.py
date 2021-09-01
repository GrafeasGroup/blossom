from datetime import datetime
from typing import Dict, List, Optional, TypedDict

from psaw import PushshiftAPI

BATCH_SIZE = 20

push = PushshiftAPI()


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


class DataEntry(TypedDict):
    done_comment: Optional[CommentData]
    tor_submission: Optional[SubmissionData]
    partner_submission: Optional[SubmissionData]
    tor_comments: Optional[List[CommentData]]
    transcriptions: Optional[List[CommentData]]


def process_done_ids(done_ids: List[str]):
    cur_index = 0
    # Process the comments in batches (we merge some of the API calls)
    while cur_index < len(done_ids):
        cur_batch = done_ids[cur_index : cur_index + BATCH_SIZE + 1]
        process_done_batch(cur_batch)
        cur_index += BATCH_SIZE


def process_done_batch(done_ids: List[str]):
    comment_filter = ["author", "body", "created_utc", "id", "link_id"]
    submission_filter = ["created_utc", "id", "permalink", "title", "url"]

    data: Dict[str, DataEntry] = {}
    for done_id in done_ids:
        data[done_id] = {}

    # First, do all the calls that we can do in batches
    # 1. Fetch the done comments from their IDs
    print("Fetching dones...")
    done_comments = list(
        push.search_comments(ids=done_ids, limit=BATCH_SIZE, filter=comment_filter,)
    )
    done_comments = [dict_from_comment(done) for done in done_comments]
    print(done_comments)
    for done_id in data:
        data[done_id]["done_comment"] = [
            done for done in done_comments if done["id"] == done_id
        ][0]
    # 2. Fetch the ToR submissions from their link id
    print("Fetching ToR submissions...")
    tor_submission_ids = [done["link_id"] for done in done_comments]
    print(tor_submission_ids)
    tor_submissions = list(
        push.search_submissions(
            ids=tor_submission_ids, limit=BATCH_SIZE, filter=submission_filter,
        )
    )
    tor_submissions = [dict_from_submission(tor_sub) for tor_sub in tor_submissions]
    print(tor_submissions)
    for done_id in data:
        done = data[done_id]["done_comment"]
        data[done_id]["tor_submission"] = [
            tor_sub
            for tor_sub in tor_submissions
            if tor_sub["id"] == done["link_id"][3:]
        ][0]
    # 3. Fetch the partner submissions from their url
    print("Fetching partner submissions...")
    partner_submission_urls = [tor_sub["url"] for tor_sub in tor_submissions]
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
    print(partner_submissions)
    for done_id in data:
        tor_sub = data[done_id]["tor_submission"]
        data[done_id]["partner_submission"] = [
            p_sub
            for p_sub in partner_submissions
            if p_sub["id"] == extract_submission_id_from_url(tor_sub["url"])
        ][0]

    # Next we need to do the individual calls
    # 1. Get comments on the ToR submission
    print("Fetching ToR comments...")
    for done_id in data:
        done = data[done_id]["done_comment"]
        tor_comments = list(
            push.search_comments(link_id=done["link_id"], filter=comment_filter)
        )
        tor_comments = [dict_from_comment(tor_com) for tor_com in tor_comments]
        data[done_id]["tor_comments"] = tor_comments
    # 2. Get transcription comments on the partner submission
    print("Fetching transcriptions...")
    for done_id in data:
        done = data[done_id]["done_comment"]
        p_sub = data[done_id]["partner_submission"]
        transcriptions = list(
            push.search_comments(
                link_id=p_sub["id"], author=done["author"], filter=comment_filter,
            )
        )
        transcriptions = [dict_from_comment(tr) for tr in transcriptions]
        data[done_id]["transcriptions"] = transcriptions

    print("DONE")
    print(data)


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


process_done_ids(["h1jacqk"])
