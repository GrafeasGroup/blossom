from copy import deepcopy

from api.models import AccountMigration
from api.slack import client
from api.slack.transcription_check.messages import reply_to_action_with_ping
from api.slack.utils import get_reddit_username, parse_user
from authentication.models import BlossomUser
from blossom.strings import translation

i18n = translation()

BASE = {"blocks": []}
HEADER_BLOCK = {
    "type": "section",
    "text": {
        "type": "mrkdwn",
        "text": (
            "Account migration requested from *{0}* to *{1}*."
            " Verify that these account names are correct before proceeding!"
        ),
    },
}
MOD_BLOCK = {
    "type": "section",
    "text": {
        "type": "plain_text",
        "text": "Approved by *u/{0}*.",
    },
}
DIVIDER_BLOCK = {"type": "divider"}
ACTION_BLOCK = {"type": "actions", "elements": []}
APPROVE_BUTTON = {
    "type": "button",
    "text": {
        "type": "plain_text",
        "text": "Approve",
    },
    "style": "primary",
    "confirm": {
        "title": {"type": "plain_text", "text": "Are you sure?"},
        "text": {
            "type": "mrkdwn",
            "text": (
                "Make sure you've doublechecked the account names"
                " before you approve this!"
            ),
        },
        "confirm": {"type": "plain_text", "text": "Do it"},
        "deny": {"type": "plain_text", "text": "Cancel"},
    },
    "value": "approve_migration_{}",
}
CANCEL_BUTTON = {
    "type": "button",
    "text": {
        "type": "plain_text",
        "text": "Cancel",
    },
    "value": "cancel_migration_{}",
    "style": "danger",
}
REVERT_BUTTON = {
    "type": "button",
    "text": {
        "type": "plain_text",
        "text": "Revert",
    },
    "confirm": {
        "title": {"type": "plain_text", "text": "Are you sure?"},
        "text": {
            "type": "mrkdwn",
            "text": (
                "Make sure you've doublechecked the account names"
                " before you approve this!"
            ),
        },
        "confirm": {"type": "plain_text", "text": "Do it"},
        "deny": {"type": "plain_text", "text": "Cancel"},
    },
    "value": "revert_migration_{}",
}


def _create_blocks(
    migration: AccountMigration, approve_cancel: bool = False, revert: bool = False
) -> dict:
    blocks = deepcopy(BASE)
    header = deepcopy(HEADER_BLOCK)
    header["text"]["text"] = HEADER_BLOCK["text"]["text"].format(
        migration.old_user.username, migration.new_user.username
    )
    blocks["blocks"].append(header)

    if migration.moderator and revert:
        # show who approved it while when we show the button to revert it
        mod_block = deepcopy(MOD_BLOCK)
        mod_block["text"]["text"] = MOD_BLOCK["text"]["text"].format(
            migration.moderator.username
        )
        blocks["blocks"].append(mod_block)

    blocks["blocks"].append(DIVIDER_BLOCK)

    action_block = deepcopy(ACTION_BLOCK)

    if approve_cancel:
        approve_button = deepcopy(APPROVE_BUTTON)
        approve_button["value"] = APPROVE_BUTTON["value"].format(migration.id)
        cancel_button = deepcopy(CANCEL_BUTTON)
        cancel_button["value"] = CANCEL_BUTTON["value"].format(migration.id)
        action_block["elements"].append(approve_button)
        action_block["elements"].append(cancel_button)

    if revert:
        revert_button = deepcopy(REVERT_BUTTON)
        revert_button["value"] = revert_button["value"].format(migration.id)
        action_block["elements"].append(revert_button)

    if len(action_block["elements"]) > 0:
        # can't have an action block with zero elements.
        blocks["blocks"].append(action_block)
    return blocks


def migrate_user_cmd(channel: str, message: str) -> None:
    """Migrate all gamma from one user to another."""
    parsed_message = message.split()
    blocks = None
    msg = None
    migration = None  # appease linter
    if len(parsed_message) < 3:
        # Needs to have two usernames
        msg = i18n["slack"]["errors"]["missing_multiple_usernames"]
    elif len(parsed_message) == 3:
        old_user, old_username = parse_user(parsed_message[1])
        new_user, new_username = parse_user(parsed_message[2])
        if not old_user:
            msg = i18n["slack"]["errors"]["unknown_username"].format(
                username=old_username
            )
        if not new_user:
            msg = i18n["slack"]["errors"]["unknown_username"].format(
                username=new_username
            )

        if old_user and new_user:
            migration = AccountMigration.objects.create(
                old_user=old_user, new_user=new_user
            )
            blocks = _create_blocks(migration, approve_cancel=True)

    else:
        msg = i18n["slack"]["errors"]["too_many_params"]

    args = {"channel": channel}
    if msg:
        args |= {"text": msg}
    if blocks:
        args |= {"blocks": blocks}

    response = client.chat_postMessage(**args)

    if blocks:
        migration.slack_channel_id = response["channel"]
        migration.slack_message_ts = response["message"]["ts"]
        migration.save()


def process_migrate_user(data: dict) -> None:
    """Handle the button responses from Slack."""
    value = data["actions"][0].get("value")
    parts = value.split("_")
    action = parts[0]
    migration_id = parts[2]
    mod_username = get_reddit_username(client, data["user"])

    migration = AccountMigration.objects.filter(id=migration_id).first()
    mod = BlossomUser.objects.filter(username=mod_username).first()

    if migration is None:
        reply_to_action_with_ping(
            data, f"I couldn't find a check with ID {migration_id}!"
        )
        return
    if mod is None:
        reply_to_action_with_ping(
            data,
            f"I couldn't find a mod with username u/{mod_username}.\n"
            "Did you set your username on Slack?",
        )
        return

    if not migration.moderator:
        migration.moderator = mod
        migration.save()

    if action == "approve":
        migration.perform_migration()
        blocks = _create_blocks(migration, revert=True)
    elif action == "revert":
        migration.revert()
        blocks = _create_blocks(migration)  # Show no buttons here.
    else:
        # maybe do something with the cancel button here?
        return

    client.chat_update(
        channel=migration.slack_channel_id,
        ts=migration.slack_message_ts,
        blocks=blocks,
    )
