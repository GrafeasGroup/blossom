"""Test the functionality of the Summary and Ping view."""
import datetime

import pytz
from django.test import Client
from django.urls import reverse
from rest_framework import status

from api.helpers import get_time_since_open
from api.models import Source, get_default_source
from api.tests.helpers import create_submission, create_user, setup_user_client


def test_ping(client: Client) -> None:
    """Test whether the ping request returns correctly."""
    result = client.get(reverse("ping"), content_type="application/json",)
    assert result.json() == {"ping?!": "PONG"}
    assert result.status_code == status.HTTP_200_OK


def test_summary(client: Client) -> None:
    """Test whether the summary request provides a correctly formatted summary."""
    client, headers, _ = setup_user_client(client)

    result = client.get(reverse("summary"), content_type="application/json", **headers,)

    assert "transcription_count" in result.json().keys()
    assert "days_since_inception" in result.json().keys()
    assert "volunteer_count" in result.json().keys()
    assert "active_volunteer_count" in result.json().keys()
    assert len(result.json().keys()) == 4
    assert result.status_code == status.HTTP_200_OK


def test_active_volunteer_count(client: Client) -> None:
    """Test whether the summary provides a correct active volunteer count."""
    client, headers, user_1 = setup_user_client(client, id=123, username="user_1")
    user_2 = create_user(id=456, username="user_2")
    user_3 = create_user(id=789, username="user_3")

    now = datetime.datetime.now(tz=pytz.utc)
    two_days_ago = now - datetime.timedelta(days=2)
    one_week_ago = now - datetime.timedelta(weeks=1)
    three_weeks_ago = now - datetime.timedelta(weeks=3)
    four_weeks_ago = now - datetime.timedelta(weeks=4)

    create_submission(completed_by=user_1, complete_time=two_days_ago)
    create_submission(completed_by=user_1, complete_time=four_weeks_ago)
    create_submission(completed_by=user_2, complete_time=three_weeks_ago)
    create_submission(completed_by=user_3, complete_time=one_week_ago)

    result = client.get(reverse("summary"), content_type="application/json", **headers,)

    assert result.status_code == status.HTTP_200_OK
    assert result.json()["active_volunteer_count"] == 2


def test_active_volunteer_count_aggregation(client: Client) -> None:
    """Test whether the active volunteer count is aggregated correctly.

    Multiple transcriptions from the same user should only count as one volunteer.
    """
    client, headers, user_1 = setup_user_client(client, id=123, username="user_1")
    user_2 = create_user(id=456, username="user_2")

    now = datetime.datetime.now(tz=pytz.utc)
    two_days_ago = now - datetime.timedelta(days=2)
    three_weeks_ago = now - datetime.timedelta(weeks=3)

    create_submission(completed_by=user_1, complete_time=two_days_ago)
    create_submission(completed_by=user_1, complete_time=two_days_ago)
    create_submission(completed_by=user_1, complete_time=two_days_ago)
    create_submission(completed_by=user_1, complete_time=three_weeks_ago)
    create_submission(completed_by=user_2, complete_time=two_days_ago)

    result = client.get(reverse("summary"), content_type="application/json", **headers,)

    assert result.status_code == status.HTTP_200_OK
    assert result.json()["active_volunteer_count"] == 2


def test_days_since_open() -> None:
    """Test whether the the output for both paths in function are the same."""
    datetuple = get_time_since_open()
    assert datetuple[0] * 365 + datetuple[1] == get_time_since_open(days=True)


def test_get_default_source() -> None:
    """Test that the function gets the Reddit source or creates if needed."""
    assert Source.objects.count() == 0
    # because this function isn't designed to be called directly, it will return
    # the ID of the record for the source.
    assert get_default_source() == "reddit"
    assert Source.objects.count() == 1
    # if we call it again, it shouldn't create something again.
    assert get_default_source() == "reddit"
    assert Source.objects.count() == 1
