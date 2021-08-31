from typing import List

from psaw import PushshiftAPI

BATCH_SIZE = 20

push = PushshiftAPI()


def process_done_ids(done_ids: List[str]):
    cur_index = 0
    # Process the comments in batches (we merge some of the API calls)
    while cur_index < len(done_ids):
        cur_batch = done_ids[cur_index : cur_index + BATCH_SIZE + 1]
        process_done_batch(cur_batch)
        cur_index += BATCH_SIZE


def process_done_batch(done_ids: List[str]):
    data = {}
    for done_id in done_ids:
        data[done_id] = {
            "done_comment": None,
            "tor_submission": None,
            "partner_submission": None,
            "tor_comments": None,
            "transcriptions": None,
        }

    # First, do all the calls that we can do in batches
    # 1. Fetch the done comments from their IDs
    print("Fetching dones...")
    done_comments = list(
        push.search_comments(
            ids=done_ids,
            limit=BATCH_SIZE,
            filter=["author", "body", "created_utc", "id", "link_id"],
        )
    )
    print(done_comments)
    for done_id in data:
        # The comments are a tuple with the attributes sorted alphabetically...
        # The id of the comment is index 3
        data[done_id]["done_comment"] = [
            done for done in done_comments if done[3] == done_id
        ][0]
    # 2. Fetch the ToR submissions from their link id
    print("Fetching ToR submissions...")
    # done[4] is link_id
    tor_submission_ids = [done[4] for done in done_comments]
    print(tor_submission_ids)
    tor_submissions = list(
        push.search_submissions(
            ids=tor_submission_ids,
            limit=BATCH_SIZE,
            filter=["created_utc", "id", "permalink", "url"],
        )
    )
    print(tor_submissions)
    for done_id in data:
        done = data[done_id]["done_comment"]
        # tor_sub[1] is id, done[4] is link_id
        data[done_id]["tor_submission"] = [
            tor_sub for tor_sub in tor_submissions if tor_sub[1] == done[4][3:]
        ][0]
    # 3. Fetch the partner submissions from their url
    print("Fetching partner submissions...")
    # tor_sub[2] is url
    partner_submission_urls = [tor_sub[2] for tor_sub in tor_submissions]
    partner_submission_ids = [
        extract_submission_id_from_url(url) for url in partner_submission_urls
    ]
    partner_submissions = list(
        push.search_submissions(
            ids=partner_submission_ids,
            limit=BATCH_SIZE,
            filter=["created_utc", "id", "permalink", "title", "url"],
        )
    )
    print(partner_submissions)
    for done_id in data:
        tor_sub = data[done_id]["tor_submission"]
        # p_sub[1] is id, tor_sub[3] is url
        print(partner_submissions[0][1])
        print(tor_sub[3])
        print(extract_submission_id_from_url(tor_sub[3]))
        data[done_id]["partner_submission"] = [
            p_sub
            for p_sub in partner_submissions
            if p_sub[1] == extract_submission_id_from_url(tor_sub[3])
        ][0]

    # Next we need to do the individual calls
    # 1. Get comments on the ToR submission
    print("Fetching ToR comments...")
    for done_id in data:
        done = data[done_id]["done_comment"]
        # done[4] is link_id
        tor_comments = list(
            push.search_comments(
                link_id=done[4], filter=["author", "body", "created_utc", "link_id"]
            )
        )
        data["tor_comments"] = tor_comments
    # 2. Get transcription comments on the partner submission
    print("Fetching transcriptions...")
    for done_id in data:
        done = data[done_id]["done_comment"]
        p_sub = data[done_id]["partner_submission"]
        # p_sub[1] is id, done[0] is author
        transcriptions = list(
            push.search_comments(
                link_id=p_sub[1],
                author=done[0],
                filter=["author", "body", "created_utc", "link_id"],
            )
        )
        data["transcriptions"] = transcriptions

    print("DONE")
    print(data)


def extract_submission_id_from_url(url: str) -> str:
    """Extracts the Reddit ID from a submission URL.
    An URL looks like this:
    https://reddit.com/r/CuratedTumblr/comments/nybt3m/medieval_medicines_and_superbugs/
    The ID of this URL would be "nybt3m".
    """
    return url.split("/")[6]


process_done_ids(["h1jacqk"])
