from typing import Any, Callable, Optional

from slack_bolt.app.app import WebClient


class Payload:
    """Payload class for everything a command needs.

    Adapted from https://github.com/grafeasgroup/utonium.
    """

    def __init__(
        self,
        # this should be a WebClient but some of our bots also define a
        # custom MockClient object, so the type hinting should accept
        # any class here.
        client: WebClient | Any = None,
        slack_payload: dict = None,
        slack_body: dict = None,
        say: Callable = None,
        context: dict = None,
    ):
        self.client = client
        self._slack_payload = slack_payload
        self._slack_body = slack_body or {}
        self._say = say
        self.context = context

        try:
            self.cleaned_text = self.clean_text(self.get_text())
        except AttributeError:
            # Sometimes we're processing payloads without text.
            self.cleaned_text = None

    command_prefixes = ["@blossom"]

    def __len__(self):
        return len(self._slack_payload)

    def try_get_command_text(self, message: str) -> Optional[str]:
        """Try to get the text content of a command.

        This checks if the message has one of the command prefixes.
        If yes, it returns the rest of the message without the prefix.
        If no, it returns `None`.
        """
        for prefix in self.command_prefixes:
            # Check if the message starts with the prefix
            if message.lower().startswith(prefix.lower()):
                # Remove the prefix from the message
                return message[len(prefix) :].strip()

        return None

    def clean_text(self, text: str | list) -> str:
        """
        Take the trigger word out of the text.

        Examples:
            !test -> !test
            !test one -> !test one
            @bubbles test -> test
            @bubbles test one -> test one
        """
        if isinstance(text, list):
            text = " ".join(text)

        return self.try_get_command_text(text) or text

    def say(self, *args, **kwargs):
        """Reply in the thread if the message was sent in a thread."""
        # Extract the thread that the message was posted in (if any)
        if self._slack_body:
            thread_ts = self._slack_body["event"].get("thread_ts")
        else:
            thread_ts = None
        return self._say(*args, thread_ts=thread_ts, **kwargs)

    def get_user(self) -> Optional[str]:
        """Get the user who sent the Slack message."""
        return self._slack_payload.get("user")

    def get_item_user(self) -> Optional[str]:
        """If this is a reaction_* obj, return the user whose content was reacted to."""
        return self._slack_payload.get("item_user")

    def is_reaction(self) -> bool:
        return self._slack_payload.get("reaction")

    def is_block_kit_action(self) -> bool:
        return self.get_event_type() in [
            "block_actions",
            "interactive_message",
            "button",
        ]

    def get_channel(self) -> Optional[str]:
        """Return the channel the message originated from."""
        return self._slack_payload.get("channel")

    def get_text(self) -> str:
        return self._slack_payload.get("text")

    def get_event_type(self) -> str:
        """
        Return the type of event that this payload is for.

        Expected types you might get are:
        - message
        - reaction_added
        - reaction_removed
        """
        return self._slack_payload.get("type")

    def get_reaction(self) -> Optional[str]:
        """
        If this is a reaction_* payload, return the emoji used.

        Example responses:
        - thumbsup
        - thumbsdown
        - blue_blog_onr
        """
        return self._slack_payload.get("reaction")

    def get_block_kit_action(self) -> Optional[str]:
        """If this is a block kit action, return the value of the action."""
        if not self.is_block_kit_action():
            return
        # If it's an action, it should have the following structure
        # https://api.slack.com/reference/interaction-payloads/block-actions#examples
        return self._slack_payload["actions"][0].get("value")

    def get_reaction_message(self) -> Optional[dict]:
        """
        If this is a reaction payload, look up the message that the reaction was for.

        This will return a full Slack response dict if the message is found or None.
        https://api.slack.com/methods/reactions.list

        Example response here:
        {
            'type': 'message',
            'channel': 'HIJKLM',
            'message': {
                'client_msg_id': '3456c594-3024-404d-9e08-3eb4fe0924c0',
                'type': 'message',
                'text': 'Sounds great, thanksss',
                'user': 'XYZABC',
                'ts': '1661965345.288219',
                'team': 'GFEDCBA',
                'blocks': [...],
                'reactions': [
                    {
                        'name': 'upvote',
                        'users': ['ABCDEFG'], 'count': 1
                    }
                ],
                'permalink': 'https://...'
            }
        }
        """
        resp = self.client.reactions_list(count=1, user=self.get_user())
        if not resp.get("ok"):
            return

        item_payload = self._slack_payload.get("item")
        if not item_payload:
            return

        target_reaction_ts = item_payload.get("ts")
        if not target_reaction_ts:
            return

        # short circuit for interactive mode
        if len(resp.get("items")) == 1 and resp["items"][0].get("channel") == "console":
            return resp["items"][0]

        for message in resp.get("items"):
            if message["message"]["ts"] == target_reaction_ts:
                return message

    def reaction_add(self, response: dict, name: str) -> Any:
        """
        Apply an emoji to a given Slack submission.

        Pass in the complete response from `say` and the name of an emoji.
        """
        return self.client.reactions_add(
            channel=response["channel"], timestamp=response["ts"], name=name
        )

    def update_message(self, response: dict, *args, **kwargs) -> Any:
        """
        Edit / update a given Slack submission.

        Pass in the complete response from `say` and your new content.
        """
        return self.client.chat_update(
            channel=response["channel"], ts=response["ts"], *args, **kwargs
        )

    def upload_file(
        self,
        file: str = None,
        title: Optional[str] = None,
        payload: Optional[dict] = None,
        content: str = None,
        filetype: str = None,  # https://api.slack.com/types/file#file_types
        initial_comment: str = None,
    ) -> Any:
        """Upload a file to a given Slack channel."""
        if (not file and not content) or (file and content):
            raise Exception("Must have either a file or content to post!")

        if not payload:
            payload = self._slack_payload
        if not title:
            title = "Just vibing."
        self.client.files_upload(
            channels=payload.get("channel"),
            file=file,
            content=content,
            filetype=filetype,
            title=title,
            as_user=True,
            initial_comment=initial_comment,
        )
