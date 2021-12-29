import pytest

from app.formatting_fixes import escape_reddit_links, redact_urls


@pytest.mark.parametrize(
    "test_input,expected_result",
    [
        ("Hi, u/a!", r"Hi, \/u/a!"),
        ("Hi, /u/a!", r"Hi, \/u/a!"),
        ("Hi, /u/a", r"Hi, \/u/a"),
        ("Hi, u/a", r"Hi, \/u/a"),
        ("something r/test_sub is cool", r"something \/r/test_sub is cool",),
        ("something /r/test_sub is cool", r"something \/r/test_sub is cool",),
        ("r/test is the best", r"\/r/test is the best"),
        ("/r/test is the best", r"\/r/test is the best"),
    ],
)
def test_escape_reddit_links(test_input: str, expected_result: str) -> None:
    """Verify that reddit pings are appropriately replaced."""
    assert escape_reddit_links(test_input) == expected_result


@pytest.mark.parametrize(
    "test_input,expected_result",
    [
        (
            "This has two valid links in it: https://aaa.com/aaa, and"
            " http://bb.com/bbb/.",
            "This has two valid links in it: <redacted link>, and <redacted link>.",
        ),
        ("Hello, https://aaaaa.com/aaa/!", "Hello, <redacted link>!"),
        (
            "Something [test](https://aaaaa.com/aaa/)",
            "Something [test](<redacted link>)",
        ),
        ("Hello, World!", "Hello, World!"),
    ],
)
def test_redact_urls(test_input: str, expected_result: str) -> None:
    """Verify that shortlinks are appropriately replaced."""
    assert redact_urls(test_input) == expected_result
