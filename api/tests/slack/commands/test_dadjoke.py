from unittest.mock import MagicMock

import pytest

from api.slack import client as slack_client
from api.slack.commands import dadjoke_cmd
from blossom.strings import translation

i18n = translation()


@pytest.mark.parametrize(
    "message", [("dadjoke"), ("dadjoke <@asdf>"), ("dadjoke a b c")],
)
def test_dadjoke_target(message: str) -> None:
    """Verify that dadjokes are delivered appropriately."""
    slack_client.chat_postMessage = MagicMock()

    dadjoke_cmd("", message, use_api=False)
    slack_client.chat_postMessage.assert_called_once()
    assert (
        i18n["slack"]["dadjoke"]["fallback_joke"]
        in slack_client.chat_postMessage.call_args[1]["text"]
    )
    if "<@" in message:
        # needs to be uppercased because otherwise slack will barf and
        # not parse it as a valid ping
        assert slack_client.chat_postMessage.call_args[1]["text"].startswith(
            "Hey <@ASDF>"
        )
    else:
        # no included username means don't use the ping formatting
        assert not slack_client.chat_postMessage.call_args[1]["text"].startswith("Hey")
