"""Test the functionality of the Summary and Ping view."""
from django.test import Client
from django.urls import reverse
from rest_framework import status

from api.helpers import get_time_since_open
from api.models import Source, get_default_source
from api.tests.helpers import setup_user_client


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
    assert len(result.json().keys()) == 3
    assert result.status_code == status.HTTP_200_OK


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
