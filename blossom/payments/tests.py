from unittest.mock import MagicMock

from django.test import Client
from django.urls import reverse


def test_payment_endpoint(client: Client, mocker: object) -> None:
    """Verify a full Stripe charge completes successfully."""
    session_obj = MagicMock()
    session_obj.id = 99

    mocker.patch("stripe.checkout.Session.create", return_value=session_obj)

    result = client.post(reverse("charge") + "?amount=7")
    assert result.status_code == 200
    assert result.json()["id"] == 99


def test_payment_no_amount(client: Client) -> None:
    """Verify we're redirected to the donation page if no amount is passed."""
    result = client.post(reverse("charge"))
    assert result.status_code == 302
    assert "giving-to-grafeas" in result.url


def test_payment_invalid_amount(client: Client) -> None:
    """Verify we're redirected to the donation page if an invalid amount is given."""
    result = client.post(reverse("charge") + "?amount=aaa")
    assert result.status_code == 302
    assert "giving-to-grafeas" in result.url
