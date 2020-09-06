import json

from django.test import Client
from django.urls import reverse
from rest_framework import status

from api.models import Source
from api.tests.helpers import get_default_test_source, setup_user_client


class TestSourceViewset:
    """Tests that validate the Source viewset is working correctly."""

    def test_list(self, client: Client) -> None:
        """Verify that listing all Source objects works correctly."""
        client, headers, _ = setup_user_client(client)
        result = client.get(
            reverse("source-list"), content_type="application/json", **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json()["count"] == 0

        source = get_default_test_source()

        result = client.get(
            reverse("source-list"), content_type="application/json", **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert result.json()["count"] == 1
        assert result.json()["results"][0]["name"] == source.name

    def test_source_create(self, client: Client) -> None:
        """Verify that creating a Source through the API works as expected."""
        client, headers, _ = setup_user_client(client)

        data = {"name": "AAA"}

        assert Source.objects.count() == 0

        result = client.post(
            reverse("source-list"),
            json.dumps(data),
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_201_CREATED
        assert Source.objects.count() == 1
        assert result.json()["name"] == data["name"]
