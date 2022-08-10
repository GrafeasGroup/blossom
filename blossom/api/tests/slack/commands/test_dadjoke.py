from unittest.mock import patch

import pytest

from blossom.api.slack.commands import dadjoke_cmd
from blossom.strings import translation

i18n = translation()


@pytest.mark.parametrize("message", ["dadjoke", "dadjoke <@asdf>", "dadjoke a b c"])
def test_dadjoke_target(message: str) -> None:
    """Verify that dadjokes are delivered appropriately."""
    with patch("blossom.api.slack.commands.dadjoke.client.chat_postMessage") as mock:
        dadjoke_cmd("", message, use_api=False)

        assert mock.call_count == 1
        assert i18n["slack"]["dadjoke"]["fallback_joke"] in mock.call_args[1]["text"]
        if "<@" in message:
            # needs to be uppercased because otherwise slack will barf and
            # not parse it as a valid ping
            assert mock.call_args[1]["text"].startswith("Hey <@ASDF>")
        else:
            # no included username means don't use the ping formatting
            assert not mock.call_args[1]["text"].startswith("Hey")
