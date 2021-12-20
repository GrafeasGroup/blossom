import re
from typing import Optional, Set

# Regex to recognize correctly formed separators.
# Separators are three dashes (---), potentially with spaces in-between.
# They need to be surrounded by
# empty lines (which can contain spaces)
# The separator line (---) can start with up to three spaces and end with arbitrary
# spaces.
PROPER_SEPARATORS_PATTERN = re.compile(r"\n[ ]*\n[ ]{,3}([-][ ]*){3,}\n")

# Regex to recognize a separator (---) being misused as heading.
# This happens when they empty line before the separator is missing.
# The following example will display as heading and not as separator:
#
# Heading
# ---
#
# The separator line can start with up to three spaces and contain spaces in-between.
HEADING_WITH_DASHES_PATTERN = re.compile(r"[\w][:*_ ]*\n[ ]{,3}([-][ ]*){3,}\n")

# Regex to recognize fenced code blocks, i.e. code blocks surrounded by three backticks.
# Example:
#
# ```
# int x = 0;
# ```
FENCED_CODE_BLOCK_PATTERN = re.compile(r"```.*```", re.DOTALL)

# Regex to recognized unescaped usernames.
# They need to be escaped with a backslash, otherwise the user will be pinged.
# For example, u/username and /u/username are not allowed.
# Instead, u\/username, \/u/username or \/u\/username should be used.
UNESCAPED_USERNAME_PATTERN = re.compile(r"(?<!\w)(?:(?<!\\)/u|(?<!/)u)(?<!\\)/\S+")

# Regex to recognized unescaped subreddit names.
# They need to be escaped with a backslash, otherwise the sub might get pinged.
# For example, r/subreddit and /u/subreddit are not allowed.
# Instead, r\/subreddit, \/r/subreddit or \/r\/subreddit should be used.
UNESCAPED_SUBREDDIT_PATTERN = re.compile(r"(?<!\w)(?:(?<!\\)/r|(?<!/)r)(?<!\\)/\S+")

# Regex to recognize unescaped hashtags which may render as headers.
# Example:
#
# #Hashtag
UNESCAPED_HEADING_PATTERN = re.compile(r"(\n[ ]*\n[ ]{,3}|^)#{1,6}[^ #]")


def check_for_heading_with_dashes(transcription: str) -> Optional[str]:
    """Check if the transcription has headings created with dashes.

    In markdown, you can make headings by putting three dashes on the next line.
    Almost always, these dashes were intended to be separators instead.

    Heading
    ---

    Will be a level 2 heading.
    """
    return (
        "heading_with_dashes"
        if HEADING_WITH_DASHES_PATTERN.search(transcription)
        else None
    )


def check_for_fenced_code_block(transcription: str) -> Optional[bool]:
    """Check if the transcription contains a fenced code block.

    Fenced code blocks look like this:

    ```
    Code Line 1
    Code Line 2
    ```

    They don't display correctly on all devices.
    """
    return True if FENCED_CODE_BLOCK_PATTERN.search(transcription) is not None else None


def check_for_unescaped_username(transcription: str) -> Optional[str]:
    r"""Check if the transcription contains an unescaped username.

    Examples: u/username and /u/username are not allowed.
    Instead, u\\/username, \\/u/username or \\/u\\/username need to be used.

    Otherwise the user will get pinged.
    """
    return (
        "unescaped_username"
        if UNESCAPED_USERNAME_PATTERN.search(transcription) is not None
        else None
    )


def check_for_unescaped_subreddit(transcription: str) -> Optional[str]:
    r"""Check if the transcription contains an unescaped subreddit name.

    Examples: r/subreddit and /r/subreddit are not allowed.
    Instead, r\\/subreddit, \\/r/subreddit or \\/r\\/subreddit need to be used.

    Otherwise the subreddit might get pinged.
    """
    return (
        "unescaped_subreddit"
        if UNESCAPED_SUBREDDIT_PATTERN.search(transcription) is not None
        else None
    )


def check_for_unescaped_heading(transcription: str) -> Optional[str]:
    """Check if the transcription contains an unescaped hashtag.

    Actual backslash in example swapped for (backslash) to avoid invalid
    escape sequence warning

    Valid: (backslash)#Text
    Valid: # Test
    Invalid: #Test
    """
    return (
        "unescaped_heading"
        if UNESCAPED_HEADING_PATTERN.search(transcription) is not None
        else None
    )


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


def check_for_formatting_issues(transcription: str) -> Set[str]:
    """Check the transcription for common formatting issues."""
    return set(
        issue
        for issue in [
            check_for_heading_with_dashes(transcription),
            check_for_unescaped_heading(transcription),
        ]
        if issue is not None
    )
