import logging
from datetime import datetime
from typing import Dict

from blossom.bootstrap import (
    END_DATE,
    LOG_FILE_PATH,
    REDDIT,
    REMOVE_ALL,
    REPORT_NOT_REMOVED,
    START_DATE,
    blossom,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler(LOG_FILE_PATH), logging.StreamHandler()],
)


def remove_on_blossom(post: Dict):
    """Remove the given submission on Blossom."""
    submission_id = post["id"]
    tor_url = post["tor_url"]
    response = blossom.patch(f"submission/{submission_id}/remove")
    if not response.ok:
        logging.error(
            f"Failed to remove submission {submission_id} ({tor_url}): "
            f"{response.status_code}\n{response.content}"
        )
    else:
        logging.info(f"Removed submission {submission_id} ({tor_url})")


def report_on_blossom(post: Dict):
    """Report the given submission on Blossom."""
    submission_id = post["id"]
    tor_url = post["tor_url"]
    response = blossom.patch(
        f"submission/{submission_id}/report",
        data={"reason": "DATA CLEANUP | Please remove on Blossom if necessary."},
    )
    if not response.ok:
        logging.error(
            f"Failed to report submission {submission_id} ({tor_url}): "
            f"{response.status_code}\n{response.content}"
        )
    else:
        logging.info(f"Reported submission {submission_id} ({tor_url})")


def sync_post_removal(post: Dict):
    """Sync the removal of the given post."""
    tor_url = post["tor_url"]
    tor_post = REDDIT.submission(url=tor_url)
    if tor_post.removed:
        if tor_post.removed_by != "tor_archivist":
            # Removed on our sub
            remove_on_blossom(post)
        else:
            partner_post = REDDIT.submission(url=tor_post.url)

            if partner_post.removed_by_category:
                # Removed on the partner sub
                remove_on_blossom(post)
            else:
                # The post has not been removed
                # Check if we should do something with it
                if REMOVE_ALL:
                    remove_on_blossom(post)
                elif REPORT_NOT_REMOVED:
                    report_on_blossom(post)


def sync_removals():
    """Sync removals on Reddit with Blossom."""
    page = 1
    page_size = 20
    post_count = 0

    logging.info(f"Processing submissions (0%)")

    while True:
        response = blossom.get(
            "submission",
            params={
                "page": page,
                "page_size": page_size,
                # Only submissions in the given time frame
                "create_time__gte": START_DATE.isoformat(),
                "create_time__lte": END_DATE.isoformat(),
                # Unclaimed submissions only
                "claimed_by__isnull": True,
                "completed_by__isnull": True,
                # Not removed already
                "removed_from_queue": False,
            },
        )
        if not response.ok:
            logging.error(
                f"Error when fetching submissions ({response.status_code})\n{response.content}"
            )
            exit(1)

        data = response.json()
        submissions = data["results"]

        # Process all submissions one by one
        for post in submissions:
            sync_post_removal(post)

        post_count += len(submissions)
        total_count = data["count"]
        percentage = post_count / total_count if total_count > 0 else 1
        logging.info(f"Processing submissions ({percentage:.0%})")

        if data["next"] is None:
            break

        page += 1

    return post_count


def main():
    """Start the script."""
    start = datetime.now()

    if blossom is None:
        logging.error("No Blossom login data provided!")
        exit(1)

    if REDDIT is None:
        logging.error("No Reddit login data provided!")
        exit(1)

    if START_DATE is None:
        logging.error("No start date provided! Please set the START_DATE env variable.")
        exit(1)

    post_count = sync_removals()

    duration = (datetime.now() - start).total_seconds()
    logging.info(f"Processed {post_count} submissions in {duration:.3f} s.")


if __name__ == "__main__":
    main()
