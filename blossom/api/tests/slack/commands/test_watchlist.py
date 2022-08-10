from unittest.mock import patch

import pytest

from blossom.api.slack.commands import watchlist_cmd
from blossom.strings import translation
from blossom.utils.test_helpers import create_user

i18n = translation()


@pytest.mark.parametrize(
    "message,expected",
    [
        (
            "watchlist",
            """*List of all watched users:*

```
100%: u/aaa
      u/bbb
 70%: u/fff
 60%: u/ccc
      u/eee
 30%: u/ddd
```""",
        ),
        (
            "watchlist percentage",
            """*List of all watched users:*

```
100%: u/aaa
      u/bbb
 70%: u/fff
 60%: u/ccc
      u/eee
 30%: u/ddd
```""",
        ),
        (
            "watchlist alphabetical",
            """*List of all watched users:*

```
u/aaa (100%)
u/bbb (100%)
u/ccc (60%)
u/ddd (30%)
u/eee (60%)
u/fff (70%)
```""",
        ),
        (
            "watchlist asdf",
            "Invalid sorting 'asdf'. Use either 'percentage' or 'alphabetical'.",
        ),
    ],
)
def test_process_watchlist(message: str, expected: str) -> None:
    """Test watchlist functionality."""
    # Test users
    # The order is scrambled intentionally to test sorting
    create_user(id=888, username="hhh", overwrite_check_percentage=None)
    create_user(id=111, username="aaa", overwrite_check_percentage=1.0)
    create_user(id=444, username="ddd", overwrite_check_percentage=0.3)
    create_user(id=222, username="bbb", overwrite_check_percentage=1.0)
    create_user(id=777, username="ggg", overwrite_check_percentage=None)
    create_user(id=555, username="eee", overwrite_check_percentage=0.6)
    create_user(id=333, username="ccc", overwrite_check_percentage=0.6)
    create_user(id=666, username="fff", overwrite_check_percentage=0.7)

    # process the message
    with patch("blossom.api.slack.commands.watchlist.client.chat_postMessage") as mock:
        watchlist_cmd("", message)
        assert mock.call_count == 1
        assert mock.call_args[1]["text"] == expected
