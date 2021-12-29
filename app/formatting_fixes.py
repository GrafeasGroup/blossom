import re

from app.validation import check_for_fenced_code_block


def clean_fenced_code_block(transcription: str) -> str:
    """Convert a fenced code block to reddit's four space formatting."""

    def cleanline(line: str) -> None:
        if "```" in line and "".join(line.split("```")).strip() == "":
            # take this line out
            pass
        else:
            line = line.replace("```", "")
            line = f"    {line}"
            temp.append(line)

    if not check_for_fenced_code_block(transcription):
        return transcription

    transcription = transcription.splitlines()
    temp = []
    codeblock: bool = False
    for line in transcription:
        if ("```" in line and not codeblock) or ("```" not in line and codeblock):
            # check if it's just ``` on its own or if it's on its own line
            cleanline(line)
            codeblock = True
        elif "```" in line and codeblock:
            cleanline(line)
            codeblock = False
        else:
            temp.append(line)

    return "\n".join(temp)


def escape_reddit_links(body: str) -> str:
    r"""
    Escape u/ and r/ links in a message.

    There is no (known) way to escape u/ or r/ (without a preceding slash),
    so those will also be changed to \/u/ and \/r/.  # noqa: W605
    :param body: the text to escape
    :return: the escaped text
    """
    body = body.replace("\r\n", "\n\n").replace(">>", r"\>\>")
    magic = re.compile(r"(?<![a-zA-Z0-9])([ur])/|/([ur])/")
    return magic.sub(r"\/\1\2/", body)


def auto_fix_formatting(transcription: str) -> str:
    """Apply automatic formatting fixes to the transcription.

    - Escape username and subreddit links in messages.
    - Convert fenced code blocks to 4 space notation.
    """
    transcription = clean_fenced_code_block(transcription)
    transcription = escape_reddit_links(transcription)

    return transcription
