from blossom.api.slack import client
from blossom.strings import translation

i18n = translation()


def help_cmd(channel: str, _message: str) -> None:
    """Post a help message to slack."""
    client.chat_postMessage(channel=channel, text=i18n["slack"]["help_message"])
