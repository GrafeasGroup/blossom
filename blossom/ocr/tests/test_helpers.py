import pytest

from blossom.ocr.helpers import _is_shortlink, escape_reddit_links, replace_shortlinks


@pytest.mark.parametrize(
    "test_input,expected_result",
    [
        ("https://aaa.com/", False),
        ("http://aaa.com/a/", True),
        ("http://aaa.com/a/a", False),
        ("https://aaa.ly/asdf", True),
        ("https://aaa.co/asdf", True),
        ("http://aaa.co", False),
        ("http://aaaaaaaaaaaaaaaa.com/", False),
        ("http://aaaaaaaaaaaaaaaa.com/aaa", False),
        ("https://aa.com/aaaaaaaaaaaaaaaaaaaaaaaa", False),
        ("http://aaaaa.com/aaa/a/a/a/a/aa/aa/a/", False),
        ("http://aaaaaaaaaaaa.com/aaa/", False),
        ("http://aaaaaaaaaaaa.com/aaa", False),
        ("http://aaa.com/a", True),
        ("http://aaa.com/aaaaaaaaaaaaa", False),
        ("http://aaa.com/a/b/c/", False),
    ],
)
def test_is_shortlink(test_input: str, expected_result: bool) -> None:
    """Verify that shorlinks are appropriately detected."""
    assert _is_shortlink(test_input) == expected_result


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
def test_replace_shortlinks(test_input: str, expected_result: str) -> None:
    """Verify that shortlinks are appropriately replaced."""
    assert replace_shortlinks(test_input) == expected_result


@pytest.mark.parametrize(
    "test_input,expected_result",
    [
        ("Hi, u/a!", "Hi, \/u/a!"),  # noqa: W605
        ("Hi, /u/a!", "Hi, \/u/a!"),  # noqa: W605
        ("Hi, /u/a", "Hi, \/u/a"),  # noqa: W605
        ("Hi, u/a", "Hi, \/u/a"),  # noqa: W605
        (
            "something r/test_sub is cool",
            "something \/r/test_sub is cool",  # noqa: W605
        ),
        (
            "something /r/test_sub is cool",
            "something \/r/test_sub is cool",  # noqa: W605
        ),
        ("r/test is the best", "\/r/test is the best"),  # noqa: W605
        ("/r/test is the best", "\/r/test is the best"),  # noqa: W605
    ],
)
def test_escape_reddit_links(test_input: str, expected_result: str) -> None:
    """Verify that reddit pings are appropriately replaced."""
    assert escape_reddit_links(test_input) == expected_result
