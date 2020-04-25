"""Test the functionality of the Summary and Ping view."""
from django.test import Client
from django_hosts import reverse
from rest_framework import status

from api.tests.helpers import setup_user_client


def test_ping(client: Client) -> None:
    """Test whether the ping request returns correctly."""
    result = client.get(
        reverse("ping", host="api"), HTTP_HOST="api", content_type="application/json",
    )
    assert result.json() == {"ping?!": "PONG"}
    assert result.status_code == status.HTTP_200_OK


def test_summary(client: Client) -> None:
    """Test whether the summary request provides a correctly formatted summary."""
    client, headers, _ = setup_user_client(client)

    result = client.get(
        reverse("summary", host="api"),
        HTTP_HOST="api",
        content_type="application/json",
        **headers,
    )

    assert "transcription_count" in result.json().keys()
    assert "days_since_inception" in result.json().keys()
    assert "volunteer_count" in result.json().keys()
    assert len(result.json().keys()) == 3
    assert result.status_code == status.HTTP_200_OK
