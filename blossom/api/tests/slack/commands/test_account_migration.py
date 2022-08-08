from unittest.mock import patch

from blossom.api.models import AccountMigration, Submission, Transcription
from blossom.api.slack.commands.migrate_user import (
    _create_blocks,
    migrate_user_cmd,
    process_migrate_user,
)
from blossom.strings import translation
from blossom.utils.test_helpers import (
    create_submission,
    create_transcription,
    create_user,
)

i18n = translation()


def test_perform_migration() -> None:
    """Verify that account migration works correctly."""
    user1 = create_user(id=100, username="Paddington")
    user2 = create_user(id=200, username="Moddington")

    submission1 = create_submission(claimed_by=user1, completed_by=user1)
    submission2 = create_submission(claimed_by=user2, completed_by=user2)

    transcription1 = create_transcription(submission=submission1, user=user1)
    transcription2 = create_transcription(submission=submission2, user=user2)

    assert Submission.objects.filter(completed_by=user1).count() == 1
    assert Submission.objects.filter(completed_by=user2).count() == 1
    assert Transcription.objects.filter(author=user1).count() == 1
    assert Transcription.objects.filter(author=user2).count() == 1

    migration = AccountMigration.objects.create(old_user=user1, new_user=user2)
    migration.perform_migration()
    assert migration.affected_submissions.count() == 1
    assert Submission.objects.filter(completed_by=user1).count() == 0
    assert Submission.objects.filter(completed_by=user2).count() == 2
    assert Transcription.objects.filter(author=user1).count() == 0
    assert Transcription.objects.filter(author=user2).count() == 2

    submission1.refresh_from_db()
    transcription1.refresh_from_db()
    transcription2.refresh_from_db()
    assert submission1.claimed_by == user2
    assert submission1.completed_by == user2
    assert transcription1.author == user2
    assert transcription2.author == user2


def test_revert() -> None:
    """Verify that reverting an account migration works."""
    user1 = create_user(id=100, username="Paddington")
    user2 = create_user(id=200, username="Moddington")

    submission1 = create_submission(claimed_by=user1, completed_by=user1)
    submission2 = create_submission(claimed_by=user2, completed_by=user2)
    transcription1 = create_transcription(submission=submission1, user=user1)
    transcription2 = create_transcription(submission=submission2, user=user2)
    assert Transcription.objects.filter(author=user1).count() == 1
    assert Transcription.objects.filter(author=user2).count() == 1

    assert Submission.objects.filter(completed_by=user1).count() == 1
    assert Submission.objects.filter(completed_by=user2).count() == 1

    migration = AccountMigration.objects.create(old_user=user1, new_user=user2)
    migration.perform_migration()

    assert Submission.objects.filter(completed_by=user1).count() == 0
    assert Submission.objects.filter(completed_by=user2).count() == 2
    assert Transcription.objects.filter(author=user1).count() == 0
    assert Transcription.objects.filter(author=user2).count() == 2
    transcription1.refresh_from_db()
    transcription2.refresh_from_db()
    assert transcription1.author == user2
    assert transcription2.author == user2

    migration.revert()

    assert Submission.objects.filter(completed_by=user1).count() == 1
    assert Submission.objects.filter(completed_by=user2).count() == 1
    assert Submission.objects.filter(completed_by=user1).count() == 1
    assert Submission.objects.filter(completed_by=user2).count() == 1

    submission1.refresh_from_db()
    transcription1.refresh_from_db()
    transcription2.refresh_from_db()
    assert submission1.claimed_by == user1
    assert submission1.completed_by == user1
    assert transcription1.author == user1
    assert transcription2.author == user2


def test_create_blocks() -> None:
    """Verify that blocks are created by default as expected."""
    user1 = create_user(id=100, username="Paddington")
    user2 = create_user(id=200, username="Moddington")
    migration = AccountMigration.objects.create(old_user=user1, new_user=user2)

    # no buttons requested
    blocks = _create_blocks(migration)
    # header and divider
    assert len(blocks) == 2
    assert "Paddington" in blocks[0]["text"]["text"]
    assert "Moddington" in blocks[0]["text"]["text"]


def test_create_blocks_with_revert_button() -> None:
    """Verify that blocks are created with the revert button as expected."""
    user1 = create_user(id=100, username="Paddington")
    user2 = create_user(id=200, username="Moddington")
    migration = AccountMigration.objects.create(old_user=user1, new_user=user2)

    blocks = _create_blocks(migration, revert=True)
    assert len(blocks) == 3
    assert len(blocks[2]["elements"]) == 1
    assert blocks[2]["elements"][0]["value"] == f"revert_migration_{migration.id}"


def test_create_blocks_with_approve_cancel_buttons() -> None:
    """Verify that blocks are created with approve and cancel buttons."""
    user1 = create_user(id=100, username="Paddington")
    user2 = create_user(id=200, username="Moddington")
    migration = AccountMigration.objects.create(old_user=user1, new_user=user2)

    blocks = _create_blocks(migration, approve_cancel=True)
    assert len(blocks) == 3
    assert len(blocks[2]["elements"]) == 2
    assert blocks[2]["elements"][0]["value"] == f"approve_migration_{migration.id}"
    assert blocks[2]["elements"][1]["value"] == f"cancel_migration_{migration.id}"


def test_create_blocks_with_mod() -> None:
    """Verify that the mod section is created appropriately."""
    user1 = create_user(id=100, username="Paddington")
    user2 = create_user(id=200, username="Bear")
    user3 = create_user(id=201, username="Mod Moddington")
    migration = AccountMigration.objects.create(
        old_user=user1, new_user=user2, moderator=user3
    )

    blocks = _create_blocks(migration, revert=True)
    assert len(blocks) == 4
    assert blocks[1] == {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Approved by *u/Mod Moddington*.",
        },
    }


def test_migrate_user_cmd() -> None:
    """Verify that the slack command for migration works as expected."""
    user1 = create_user(id=100, username="Paddington")
    user2 = create_user(id=200, username="Moddington")

    assert AccountMigration.objects.count() == 0

    with patch(
        "blossom.api.slack.commands.migrate_user.client.chat_postMessage"
    ) as mock:
        mock.return_value = {"channel": "AAA", "message": {"ts": 1234}}
        migrate_user_cmd(channel="abc", message="migrate paddington moddington")

    mock.assert_called_once()
    assert len(mock.call_args.kwargs["blocks"]) == 3
    assert mock.call_args.kwargs["channel"] == "abc"

    assert AccountMigration.objects.count() == 1
    migration = AccountMigration.objects.first()
    assert migration.old_user == user1
    assert migration.new_user == user2
    assert migration.slack_channel_id == "AAA"
    assert migration.slack_message_ts == "1234"


def test_migrate_user_cmd_missing_users() -> None:
    """Verify error for missing users."""
    with patch(
        "blossom.api.slack.commands.migrate_user.client.chat_postMessage"
    ) as mock:
        migrate_user_cmd(channel="abc", message="migrate")

    # no blocks when there's text here
    assert mock.call_args.kwargs.get("blocks") is None
    assert (
        mock.call_args.kwargs["text"]
        == i18n["slack"]["errors"]["missing_multiple_usernames"]
    )
    assert mock.call_args.kwargs["channel"] == "abc"


def test_migrate_user_cmd_wrong_first_user() -> None:
    """Verify error for missing first user."""
    create_user(id=100, username="Paddington")
    with patch(
        "blossom.api.slack.commands.migrate_user.client.chat_postMessage"
    ) as mock:
        migrate_user_cmd(channel="abc", message="migrate AAAA Paddington")

    # no blocks when there's text here
    assert mock.call_args.kwargs.get("blocks") is None
    assert mock.call_args.kwargs["text"] == i18n["slack"]["errors"][
        "unknown_username"
    ].format(username="AAAA")
    assert mock.call_args.kwargs["channel"] == "abc"


def test_migrate_user_cmd_wrong_second_user() -> None:
    """Verify error for missing second user."""
    create_user(id=100, username="Paddington")
    with patch(
        "blossom.api.slack.commands.migrate_user.client.chat_postMessage"
    ) as mock:
        migrate_user_cmd(channel="abc", message="migrate Paddington BBBB")

    assert mock.call_args.kwargs.get("blocks") is None
    assert mock.call_args.kwargs["text"] == i18n["slack"]["errors"][
        "unknown_username"
    ].format(username="BBBB")
    assert mock.call_args.kwargs["channel"] == "abc"


def test_migrate_user_cmd_too_many_users() -> None:
    """Verify error for too many users."""
    with patch(
        "blossom.api.slack.commands.migrate_user.client.chat_postMessage"
    ) as mock:
        migrate_user_cmd(channel="abc", message="migrate A B C")

    assert mock.call_args.kwargs.get("blocks") is None
    assert mock.call_args.kwargs["text"] == i18n["slack"]["errors"]["too_many_params"]
    assert mock.call_args.kwargs["channel"] == "abc"


def test_process_migrate_user() -> None:
    """Verify migration works when called via buttons."""
    user1 = create_user(id=100, username="Paddington")
    user2 = create_user(id=200, username="Moddington")

    create_submission(claimed_by=user1, completed_by=user1)
    create_submission(claimed_by=user2, completed_by=user2)

    assert Submission.objects.filter(completed_by=user1).count() == 1
    assert Submission.objects.filter(completed_by=user2).count() == 1

    migration = AccountMigration.objects.create(
        old_user=user1, new_user=user2, slack_message_ts=123, slack_channel_id="AAA"
    )

    with patch(
        "blossom.api.slack.commands.migrate_user.get_reddit_username",
        lambda _, us: us["name"],
    ), patch(
        "blossom.api.slack.commands.migrate_user.client.chat_update"
    ) as message_mock, patch(
        "blossom.api.slack.commands.migrate_user.reply_to_action_with_ping",
        return_value={},
    ) as reply_mock:
        process_migrate_user(
            {
                "actions": [{"value": f"approve_migration_{migration.id}"}],
                "user": {"name": "Moddington"},
            }
        )

    assert Submission.objects.filter(completed_by=user1).count() == 0
    assert Submission.objects.filter(completed_by=user2).count() == 2

    message_mock.assert_called_once()
    # header, mod approved, divider, revert button
    assert len(message_mock.call_args.kwargs["blocks"]) == 4

    revert_button = message_mock.call_args.kwargs["blocks"][3]["elements"][0]
    assert revert_button["value"] == f"revert_migration_{migration.id}"

    with patch(
        "blossom.api.slack.commands.migrate_user.get_reddit_username",
        lambda _, us: us["name"],
    ), patch(
        "blossom.api.slack.commands.migrate_user.client.chat_update"
    ) as message_mock, patch(
        "blossom.api.slack.commands.migrate_user.reply_to_action_with_ping",
        return_value={},
    ) as reply_mock:
        process_migrate_user(
            {
                "actions": [{"value": f"revert_migration_{migration.id}"}],
                "user": {"name": "Moddington"},
            }
        )

    assert Submission.objects.filter(completed_by=user1).count() == 1
    assert Submission.objects.filter(completed_by=user2).count() == 1

    # we've reverted -- no more buttons for you
    assert len(message_mock.call_args.kwargs["blocks"]) == 3

    with patch(
        "blossom.api.slack.commands.migrate_user.get_reddit_username",
        lambda _, us: us["name"],
    ), patch(
        "blossom.api.slack.commands.migrate_user.client.chat_update"
    ) as message_mock, patch(
        "blossom.api.slack.commands.migrate_user.reply_to_action_with_ping",
        return_value={},
    ) as reply_mock:
        process_migrate_user(
            {
                "actions": [{"value": f"cancel_migration_{migration.id}"}],
                "user": {"name": "Moddington"},
            }
        )

    message_mock.assert_called_once()
    assert (
        message_mock.call_args.kwargs["blocks"][-1]["text"]["text"]
        == "Action cancelled."
    )

    reply_mock.assert_not_called()


def test_migrate_user_no_migration() -> None:
    """Verify error for nonexistent migration."""
    create_user(id=200, username="Moddington")

    with patch(
        "blossom.api.slack.commands.migrate_user.get_reddit_username",
        lambda _, us: us["name"],
    ), patch(
        "blossom.api.slack.commands.migrate_user.client.chat_update"
    ) as message_mock, patch(
        "blossom.api.slack.commands.migrate_user.reply_to_action_with_ping",
        return_value={},
    ) as reply_mock:
        process_migrate_user(
            {
                "actions": [{"value": "approve_migration_1"}],
                "user": {"name": "Moddington"},
            }
        )

    message_mock.assert_not_called()
    reply_mock.assert_called_once()
    assert reply_mock.call_args.args[-1] == "I couldn't find a check with ID 1!"


def test_migrate_user_wrong_username() -> None:
    """Verify error for wrong mod username on Slack."""
    user1 = create_user(id=200, username="Moddington")

    migration = AccountMigration.objects.create(old_user=user1, new_user=user1)

    with patch(
        "blossom.api.slack.commands.migrate_user.get_reddit_username",
        lambda _, us: us["name"],
    ), patch(
        "blossom.api.slack.commands.migrate_user.client.chat_update"
    ) as message_mock, patch(
        "blossom.api.slack.commands.migrate_user.reply_to_action_with_ping",
        return_value={},
    ) as reply_mock:
        process_migrate_user(
            {
                "actions": [{"value": f"approve_migration_{migration.id}"}],
                "user": {"name": "AA"},
            }
        )

    message_mock.assert_not_called()
    reply_mock.assert_called_once()
    assert "I couldn't find a mod with username u/AA." in reply_mock.call_args.args[-1]
