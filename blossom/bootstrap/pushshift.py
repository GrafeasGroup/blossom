import logging
import re

from psaw import PushshiftAPI

from blossom.bootstrap.helpers import get_transcribot_comment, get_transcribot_text
from blossom.bootstrap.reddit_comment_tree import RedditCommentTree

api = PushshiftAPI()
logger = logging.getLogger(__name__)


def get_transcription_data_from_pushshift(comment_id: str):
    """
    We start with the ID of a comment in a thread. What we need is the following:

    * the other comments in the thread that our comment is in
    * the post that the thread links to
    * the comments from that thread

    :param comment_id:
    :return: the post on r/ToR, the comment object that holds the transcription,
        and the full comments from the post that was transcribed
    """
    return None, None, None, None
    post_regex = r"\/comments\/?([a-z0-9]+)\/"

    # Get the actual comment object that we have the ID for
    comment_result = next(
        iter(list(api.search_comments(ids=comment_id, limit=1))), None
    )
    if comment_result is None:
        # something went horribly wrong
        return None, None, None, None
    # start down the rabbit hole
    # grab the post on r/ToR that has the comment in it
    link_id = comment_result.link_id
    tor_result = next(iter(list(api.search_submissions(ids=link_id, limit=1))), None)
    # tor_result = requests.get(f'https://api.pushshift.io/reddit/search/submission/?ids={link_id}')

    if tor_result is None:
        # well, fuck. Something horrible went wrong.
        return None, None, None, None

    # okay, now we have the post that we were meant to be transcribing
    linked_url = tor_result.url
    linked_id = re.search(post_regex, linked_url).groups()[0]

    # there doesn't seem to be a good way to get this data from inside psaw, so
    # we'll dance without the rate limit check and hope we don't push it too
    # much
    # comment_ids = requests.get(
    #     f"https://api.pushshift.io/reddit/submission/comment_ids/{linked_id}"
    # )
    # if int(comment_ids.status_code) == 200:
    #     comment_ids = comment_ids.json()["data"]
    # else:
    #     return None, None

    # Example:
    # https://api.pushshift.io/reddit/comment/search?ids=dlrezc8,dlrawgw,dlrhbkq

    c_result = list(api.search_comments(link_id=linked_id))
    for item in c_result:
        # only grab the comment if it has part of the footer and is a top-level
        # comment
        if (
            "/r/transcribersofreddit/wiki/index)" in item.body.lower()
            and item.parent_id.startswith("t3_")
        ):
            return tor_result, item, linked_id, c_result

    return tor_result, None, None, None


def get_tor_claim_and_done_from_pushshift(post):
    # comment_ids = (
    #     requests.get(
    #         f"https://api.pushshift.io/reddit/submission/comment_ids/{post_id}"
    #     )
    #     .json()
    #     .get("data")
    # )
    #
    # if not comment_ids:
    #     return None, None

    if post is None:
        logger.info("Received None for post! There's nothing to look for.")
        return None, None, None, None

    claim = None
    done = None

    c_results = list(api.search_comments(link_id=post.id))
    transcribot_text = get_transcribot_text(c_results, post.id)
    transcribot_comment = get_transcribot_comment(c_results, post.id)
    for c in c_results:
        # this is more complicated than it needs to be because of people
        # who posted one comment for claim and done (_cough_ @captcoe) and
        # people who like to write long-ass comments for the hell of it that
        # abuse the order of operations for the bot (_cough_ @queq, @lukeabby)
        # Also, people delete the comments (grrrr) so it's entirely possible
        # that these still end up being None.

        if "claim" in c.body and "done" in c.body:
            return c, c, transcribot_text, transcribot_comment

        if "claim" in c.body and "done" not in c.body:
            claim = c

        if "claim" not in c.body and "done" in c.body:
            done = c

    return claim, done, transcribot_text, transcribot_comment


def get_extended_transcript_body(comment, post_id, all_comments):
    """
    We have the top level comment that is our transcription, but sometimes
    they're super long and form a chain of comments. According to our official
    recommendations, long transcriptions should be a chain of comments that
    all reply to each other with each one having the footer. We'll be a little
    easier on them (just check to see if the author of the immediate comment
    is from the same author, as any comment they make that immediately replies
    to a transcription is either more transcription or more context for that
    transcription).
    """

    tree = RedditCommentTree(all_comments, post_id)
    return tree.find_transcription()
