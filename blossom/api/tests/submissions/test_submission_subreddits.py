# Disable line length restrictions to allow long URLs
# flake8: noqa: E501
from collections import OrderedDict

from django.test import Client
from django.urls import reverse
from rest_framework import status

from blossom.utils.test_helpers import create_submission, setup_user_client


class TestSubreddits:
    """Tests to validate that the subreddit data is generated correctly."""

    def test_subreddit_extraction(self, client: Client) -> None:
        """Test that the subreddit of a single submission is determined correctly."""
        client, headers, user = setup_user_client(client, accepted_coc=True, id=123456)

        create_submission(
            url="https://reddit.com/r/ProgrammerHumor/comments/11e845g/think_smart_not_hard/"
        )

        result = client.get(
            reverse("submission-subreddits"),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK

        expected_subreddits = OrderedDict(ProgrammerHumor=1)
        subreddits = result.json()
        assert subreddits == expected_subreddits

    def test_subreddit_aggregation(self, client: Client) -> None:
        """Test that multiple submissions from the same subreddit are aggregated."""
        client, headers, user = setup_user_client(client, accepted_coc=True, id=123456)

        create_submission(
            url="https://reddit.com/r/ProgrammerHumor/comments/11e845g/think_smart_not_hard/"
        )
        create_submission(
            url="https://reddit.com/r/ProgrammerHumor/comments/11e88ls/then_what_do_you_do/"
        )
        create_submission(
            url="https://reddit.com/r/CuratedTumblr/comments/11e232j/life_is_nuanced_and_complex/"
        )
        create_submission(
            url="https://reddit.com/r/ProgrammerHumor/comments/11e42w6/yes_i_know_about_transactions_and_backups/"
        )
        create_submission(
            url="https://reddit.com/r/CuratedTumblr/comments/11ds7gc/big_boss_was_down_bad/"
        )

        result = client.get(
            reverse("submission-subreddits"),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK

        expected_subreddits = OrderedDict(ProgrammerHumor=3, CuratedTumblr=2)
        subreddits = result.json()
        assert subreddits == expected_subreddits

    def test_submission_filters(self, client: Client) -> None:
        """Test that the normal submission filters work."""
        client, headers, user = setup_user_client(client, accepted_coc=True, id=123456)

        create_submission(
            url="https://reddit.com/r/ProgrammerHumor/comments/11e845g/think_smart_not_hard/",
            completed_by=user,
        )
        create_submission(
            url="https://reddit.com/r/ProgrammerHumor/comments/11e88ls/then_what_do_you_do/"
        )

        result = client.get(
            reverse("submission-subreddits") + "?completed_by=123456",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK

        expected_subreddits = OrderedDict(ProgrammerHumor=1)
        subreddits = result.json()
        assert subreddits == expected_subreddits
