import pytest

from app.formatting_fixes import escape_reddit_links


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
