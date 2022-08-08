from blossom.api.slack import client
from blossom.strings import translation

i18n = translation()


def ping_cmd(channel: str, _message: str) -> None:
    """Respond to pings."""
    client.chat_postMessage(channel=channel, text="PONG!")
