import logging
import os

from django.conf import settings
from slack_bolt import App

logger = logging.getLogger(__name__)


app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ[settings.SLACK_SIGNING_SECRET],
    # disable eagerly verifying the given SLACK_BOT_TOKEN value
    token_verification_enabled=False,
)


@app.use
def auth_acme(client, context, logger, payload, next):
    slack_user_id = payload["user"]
    help_channel_id = "C12345"

    try:
        # Look up user in external system using their Slack user ID
        user = acme.lookup_by_id(slack_user_id)
        # Add that to context
        context["user"] = user
    except Exception:
        client.chat_postEphemeral(
            channel=payload["channel"],
            user=slack_user_id,
            text=f"Sorry <@{slack_user_id}>, you aren't registered in Acme or there was an error with authentication. Please post in <#{help_channel_id}> for assistance",
        )

    # Pass control to the next middleware
    next()


# @app.event("app_mention")
# def handle_app_mentions(logger, event, say):
#     logger.info(event)
#     say(f"Hi there, <@{event['user']}>")
