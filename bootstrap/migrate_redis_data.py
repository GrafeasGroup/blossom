import time
from datetime import datetime
from typing import Dict, List, Optional, TypedDict

from psaw import PushshiftAPI

BATCH_SIZE = 20

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


class DataEntry(TypedDict):
    done_comment: Optional[CommentData]
    tor_submission: Optional[SubmissionData]
    partner_submission: Optional[SubmissionData]
    tor_comments: Optional[List[CommentData]]
    transcriptions: Optional[List[CommentData]]


Data = Dict[str, DataEntry]


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


def process_done_batch(done_ids: List[str]):
    data: Dict[str, DataEntry] = {}
    for done_id in done_ids:
        data[done_id] = {
            "done_comment": None,
            "tor_submission": None,
            "partner_submission": None,
            "tor_comments": None,
            "transcriptions": None,
        }

    # First, do all the calls that we can do in batches
    fetch_done_comments(data)
    fetch_tor_submissions(data)
    fetch_partner_submissions(data)
    # Next we need to do the individual calls
    fetch_tor_comments(data)
    fetch_transcriptions(data)


def fetch_done_comments(data: Data) -> Data:
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


def fetch_tor_submissions(data: Data) -> Data:
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


def fetch_partner_submissions(data: Data) -> Data:
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


def fetch_tor_comments(data: Data) -> Data:
    print("Fetching ToR comments...", end=" ")
    start = time.time()
    found_count = 0
    not_found_count = 0
    for done_id in data:
        done = data[done_id]["done_comment"]
        if done is None:
            continue
        tor_comments = list(
            push.search_comments(link_id=done["link_id"], filter=comment_filter)
        )
        tor_comments = [dict_from_comment(tor_com) for tor_com in tor_comments]
        if len(tor_comments) > 0:
            data[done_id]["tor_comments"] = tor_comments
            found_count += 1
        else:
            not_found_count += 1

    dur = time.time() - start
    print(f"{found_count}/{found_count + not_found_count} found in {dur:.2f} s.")
    return data


def fetch_transcriptions(data: Data) -> Data:
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


process_done_ids(
    [
        "eje5ndq",
        "eje65me",
        "eje6f1y",
        "eje743p",
        "eje7tsx",
        "eje8fjf",
        "ejeb6r8",
        "ejebabk",
        "ejebfcb",
        "ejebnh0",
        "ejebs30",
        "ejebwk5",
        "ejec2c6",
        "ejec8ik",
        "ejgeoqa",
        "ejgewef",
        "ejgffh7",
        "ejgfrn5",
        "ejh30n1",
        "ejh36hq",
        "ejh3edh",
        "ejh3pgj",
        "ejh3vdb",
        "ejh4bso",
        "ejj6lda",
        "ejj6sam",
        "ejj6xp4",
        "ejj71gw",
        "ejj78i3",
        "ejj7k2x",
        "ejj7ujj",
        "ejjgasl",
        "ejjghwm",
        "ejjgqra",
        "ejm5uca",
        "ejm696s",
        "ejm6fw2",
        "ejm6nqc",
        "ejm6u1m",
        "ejm74g0",
        "ejm7bap",
        "ejm7fxs",
        "ejm7mhs",
        "ejm7sta",
        "ejmsa4f",
        "ejmsfjs",
        "ejmskpm",
        "ejmsunp",
        "ejmsz59",
        "ejmt35a",
        "ejmtn3e",
        "ejmts2u",
        "ejp3sen",
        "ejp3x05",
        "ejp4155",
        "ejpnmld",
        "ejpnpkn",
        "ejpnwsc",
        "ejpo29e",
        "ejpoh2a",
        "ejpon0x",
        "ejpoq6h",
        "ejpospn",
        "ejpouu7",
        "ejpp0ex",
        "ejpp5gp",
        "ejpt7j9",
        "ejptcvo",
        "ejptjg0",
        "ejptmcu",
        "ejptp5q",
        "ejpts42",
        "ejptubk",
        "ejptxuk",
        "ejpu3q2",
        "ejpu7vp",
        "ejpubj0",
        "ejpufcf",
        "ejpukrr",
        "ejpun2d",
        "ejpupy3",
        "ejpurnw",
        "ejpuup7",
        "ejpuxkq",
        "ejpv0ju",
        "ejpv28f",
        "ejpv4l8",
        "ejpv8zm",
        "ejpvddj",
        "ejpvfsu",
        "ejpvgvf",
        "ejpvkt0",
        "ejpvni9",
        "ejpvoaz",
        "ejpvy1g",
        "ejpvz8u",
        "ejpw2d1",
        "ejpw6zq",
        "ejpwbue",
        "ejpweaf",
        "ejpwg7u",
        "ejpwj5p",
        "ejpwk3x",
        "ejpwmb3",
        "ejpwoa6",
        "ejpwpm0",
        "ejqnl2z",
        "ejqnqzo",
        "ejqo1lt",
        "ejqofgt",
        "ejqojs9",
        "ejqoqle",
        "ejqoudb",
        "ejqp04m",
        "ejqpahd",
        "ejqpipw",
        "ejqpndj",
        "ejqpxvo",
        "ejqq2ad",
        "ejqq9jy",
        "ejqqgj2",
        "ejqqm3p",
        "ejqqqa2",
        "ejqqwy0",
        "ejqr1d3",
        "ejqrb3t",
        "ejqrhgv",
        "ejqrkdp",
        "ejqrq9p",
        "ejqruh5",
        "ejqrz3p",
        "ejqs2cq",
        "ejqs6fw",
        "ejqs9w6",
        "ejqshg1",
        "ejqsm8p",
        "ejqsrwp",
        "ejqt2nv",
        "ejqt7b0",
        "ejqtblx",
        "ejqtjej",
        "ejqu6t8",
        "ejqyafq",
        "ejqyfy5",
        "ejqyisf",
        "ejqyn1b",
        "ejqyv97",
        "ejqz18x",
        "ejqz8e3",
        "ejqzjd4",
        "ejr3623",
        "ejr39bb",
        "ejr3e6w",
        "ejr3mdm",
        "ejr3q0d",
        "ejr4ydl",
        "ejr5396",
        "ejr57ow",
        "ejr5eq0",
        "ejr5q4o",
        "ejr5t8l",
        "ejr85r7",
        "ejr88vd",
        "ejr8fgi",
        "ejr8mt7",
        "ejr9d4w",
        "ejr9h4y",
        "ejritq8",
        "ejrivh5",
        "ejrizhx",
        "ejrj4dk",
        "ejrj9n7",
        "ejrjel3",
        "ejrjib9",
    ]
)
