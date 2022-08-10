"""A script to fix multi comment transcriptions in Blossom.

Due to a bug, only the first comment of multi-comment transcriptions
was sent to Blossom.
"""
import logging
from datetime import datetime
from typing import Dict, List

from psaw import PushshiftAPI

from blossom.bootstrap import END_DATE, START_DATE, blossom
from blossom.bootstrap.migrate_redis_data import (
    CommentData,
    comment_filter,
    dict_from_comment,
    extract_id_from_grafeas_url,
)

push = PushshiftAPI()


def _get_link_id(tr: Dict) -> str:
    """Get the Reddit link ID of the given transcription.

    For https://reddit.com/r/worldnewsvideo/comments/s48db9/bronx_fire_landlord_had_history_of_neglecting_heat/hss8wz0/
    it returns s48db9.
    """
    return tr["url"].split("/")[6]


def _remove_footer(transcription: str) -> str:
    """Remove the footer of the transcription."""
    parts = transcription.split("---")
    if len(parts) < 3:
        logging.warning(f"Weird transcription format:\n{transcription}")
        return transcription

    return "---".join(parts[:-1]).strip()


def _join_transcriptions(transcriptions: List[CommentData]) -> str:
    """Join a multi-comment transcription into a single text."""
    texts = [tr["body"] for tr in transcriptions]
    first_texts = texts[:-1]
    # Remove the footers in the middle
    combined_texts = [_remove_footer(txt) for txt in first_texts] + [texts[-1].strip()]
    return "\n\n---\n\n".join(combined_texts)


def fix_multi_comment_transcription(transcription: Dict):
    """Fix a multi comment transcription in Blossom."""
    if not (7000 < len(transcription["text"]) < 10050):
        # If we have an unprocessed first comment of a multi-comment transcription,
        # it will be rather long, but shorter than ~10000 characters (with a small buffer)
        return

    # Get the transcription author
    tr_id = transcription["id"]
    tr_url = transcription["url"]
    author_id = extract_id_from_grafeas_url(transcription["author"])
    author_response = blossom.get(f"volunteer/{author_id}")
    if not author_response.ok:
        logging.error(
            f"Failed to fetch author {author_id} for transcription {tr_id} {tr_url}!"
            f"({author_response.status_code})"
        )
        return
    author = author_response.json()

    # Get the transcription comments from Pushshift
    transcriptions = list(
        push.search_comments(
            link_id=_get_link_id(transcription),
            author=author["username"],
            filter=comment_filter,
        )
    )
    transcriptions: List[CommentData] = [dict_from_comment(x) for x in transcriptions]
    # Make sure the comments are actually transcriptions
    transcriptions = [
        x
        for x in transcriptions
        if "https://www.reddit.com/r/TranscribersOfReddit/wiki/index" in x["body"]
        and "#32;" in x["body"]
    ]

    if len(transcriptions) == 0:
        logging.error(f"No comments found for transcription {tr_id} {tr_url}!")
        return

    if len(transcriptions) < 2:
        logging.info(f"Transcription {tr_id} does not have multiple comments. {tr_url}")
        return

    transcriptions.sort(key=lambda x: x["created_utc"])

    # Assemble the transcription text
    text = _join_transcriptions(transcriptions)
    if (len(text) - 10) < len(transcription["text"]):
        logging.warning(
            f"New transcription is shorter than old transcription {tr_id} {tr_url}, skipping."
        )
        return

    # Update the transcription in Blossom
    update_response = blossom.patch(f"transcription/{tr_id}", data={"text": text})
    if not update_response.ok:
        logging.error(
            f"Failed to update transcription {tr_id} {tr_url} "
            f"({update_response.status_code}\n{update_response.content}"
        )
        return

    logging.info(f"Updated transcription {tr_id} with multiple comments {tr_url}")


def fix_multi_comment_transcriptions() -> int:
    """Fix multi comment transcriptions in Blossom."""
    page = 1
    page_size = 100
    tr_count = 0

    logging.info(f"Processing transcriptions (0%)")

    while True:
        response = blossom.get(
            "transcription",
            params={
                "page": page,
                "page_size": page_size,
                # Only transcriptions in the given time frame
                "create_time__gte": START_DATE.isoformat(),
                "create_time__lte": END_DATE.isoformat(),
                "removed_on_reddit": False,
            },
        )
        if not response.ok:
            logging.error(
                f"Error when fetching transcriptions ({response.status_code})\n{response.content}"
            )
            exit(1)

        data = response.json()
        transcriptions = data["results"]

        # Process all submissions one by one
        for tr in transcriptions:
            fix_multi_comment_transcription(tr)

        tr_count += len(transcriptions)
        total_count = data["count"]
        percentage = tr_count / total_count if total_count > 0 else 1
        logging.info(f"Processing transcriptions ({percentage:.0%})")

        if data["next"] is None:
            break

        page += 1

    return tr_count


def main():
    start = datetime.now()

    if blossom is None:
        logging.error("No Blossom login data provided!")
        exit(1)

    if START_DATE is None:
        logging.error("No start date provided! Please set the START_DATE env variable.")
        exit(1)

    tr_count = fix_multi_comment_transcriptions()

    duration = (datetime.now() - start).total_seconds()
    logging.info(f"Processed {tr_count} transcriptions in {duration:.3f} s.")


if __name__ == "__main__":
    main()
