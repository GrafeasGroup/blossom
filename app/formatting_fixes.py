import re

from app.validation import check_for_fenced_code_block

# Simplified URL regex adapted from https://stackoverflow.com/a/3809435
# It ensures that URLs aren't allowed to end with a dot
URL_RE = re.compile(r"(https?://|www\.)[\w\-_@:%/+~#=.]*[\w\-_@:%/+~#=]")


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


def escape_reddit_links(transcription: str) -> str:
    r"""Escape u/ and r/ links in a message.

    There is no (known) way to escape u/ or r/ (without a preceding slash),
    so those will also be changed to \/u/ and \/r/.  # noqa: W605
    :param transcription: the text to escape
    :return: the escaped text
    """
    magic = re.compile(r"(?<![a-zA-Z0-9])([ur])/|/([ur])/")
    return magic.sub(r"\/\1\2/", transcription)


def fix_line_endings(transcription: str) -> str:
    """Convert CRLF to LF."""
    return transcription.replace("\r\n", "\n")


def line_breaks_to_paragraphs(transcription: str) -> str:
    """Convert a normal line break to a new paragraph.

    This is necessary to properly render the line break in Markdown.
    """
    return transcription.replace("\n", "\n\n")


def escape_markdown_formatting(transcription: str) -> str:
    """Escape some markdown formatting so that it renders the characters literally.

    - Headings
    - Quotes
    - Lists
    - Horizontal separators
    - Italics/Bold
    """
    return (
        # Headings
        transcription.replace("#", r"\#")
        # Quotes
        .replace(">", r"\>")
        # Lists/Horizontal separators
        .replace("-", r"\-")
        # Italics/Bold
        .replace("*", r"\*").replace("_", r"\_")
    )


def redact_urls(transcription: str, replacement: str = "<redacted link>") -> str:
    """Replace all URLs with a redaction string."""
    return URL_RE.sub(replacement, transcription)


def auto_fix_user_formatting(transcription: str) -> str:
    """Apply automatic formatting fixes to the transcription of a user."""
    transcription = fix_line_endings(transcription)
    transcription = clean_fenced_code_block(transcription)
    transcription = escape_reddit_links(transcription)

    return transcription


def auto_fix_ocr_formatting(transcription: str) -> str:
    """Apply automatic formatting fixes to the transcription of an OCR bot."""
    transcription = fix_line_endings(transcription)
    transcription = clean_fenced_code_block(transcription)
    transcription = escape_reddit_links(transcription)
    transcription = redact_urls(transcription)

    return transcription
