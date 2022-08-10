import requests

from blossom.api.slack import client
from blossom.strings import translation

i18n = translation()


def dadjoke_cmd(channel: str, message: str, use_api: bool = True) -> None:
    """Send the pinged user a dad joke. Or just send everybody a joke."""
    parsed_message = message.split()
    ping_username, msg = None, None
    try:
        if use_api:
            joke = requests.get(
                "https://icanhazdadjoke.com/", headers={"Accept": "text/plain"}
            ).content.decode()
        else:
            raise Exception("Testing mode -- just use fallback.")
    except:  # noqa: E722
        joke = i18n["slack"]["dadjoke"]["fallback_joke"]

    if len(parsed_message) == 2:
        if parsed_message[1].startswith("<"):
            ping_username = parsed_message[1].upper()

        if ping_username:
            msg = i18n["slack"]["dadjoke"]["message"].format(ping_username, joke)

    if not msg:
        msg = joke

    client.chat_postMessage(channel=channel, text=msg, link_names=True)
