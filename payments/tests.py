import pytest
import requests
import stripe
from django.conf import Settings
from django.test import Client
from django.urls import reverse

# NOTE: In order to test slack, you must add the `settings` hook and set
# `settings.ENABLE_SLACK = True`. MAKE SURE that if you're writing a new
# test that uses ENABLE_SLACK that you patch `requests.post` or it will
# try and ping modchat (if you're running locally) or explode if this is
# running in the github actions pipeline.


def test_payment_endpoint_with_get_request(client: Client) -> None:
    """Verify that a web browser accessing the payment endpoint will be turned away."""
    result = client.get(reverse("charge"))
    assert result.status_code == 200
    assert result.content == b"go away"


def test_payment_endpoint(
    client: Client, mocker: object, setup_site: object, settings: Settings
) -> None:
    """Verify a full Stripe charge completes successfully."""
    settings.ENABLE_SLACK = True
    mocker.patch("requests.post")
    mocker.patch("stripe.Charge")
    stripe.Charge.create.return_value = {"status": "succeeded"}

    data = {"stripeToken": "asdf", "amount": "300", "stripeEmail": "a@a.com"}

    result = client.post(reverse("charge"), data)
    assert result.status_code == 302
    assert "thank-you" in result.url
    requests.post.assert_called_once()
    assert "live" in stripe.api_key
    stripe.Charge.create.assert_called_once()
    # post going to #org-running
    assert "channel" not in requests.post.call_args.kwargs.get("json")


def test_payment_endpoint_debug_mode(
    client: Client, mocker: object, setup_site: object, settings: Settings
) -> None:
    """Verify that the test key is used when Blossom is in debug mode."""
    settings.DEBUG = True
    settings.ENABLE_SLACK = True
    mocker.patch("requests.post")
    mocker.patch("stripe.Charge")
    stripe.Charge.create.return_value = {"status": "succeeded"}

    data = {"stripeToken": "asdf", "amount": "300", "stripeEmail": "a@a.com"}

    client.post(reverse("charge"), data)

    requests.post.assert_called_once()
    assert "test" in stripe.api_key
    stripe.Charge.create.assert_called_once()
    # post going to #org-running
    assert "channel" in requests.post.call_args.kwargs.get("json")


def test_failed_charge(client: Client, mocker: object, settings: Settings) -> None:
    """Verify that a failed charge attempt through Stripe notifies Slack."""
    settings.ENABLE_SLACK = True
    mocker.patch("requests.post")
    mocker.patch("stripe.Charge")
    stripe.Charge.create.return_value = {"status": "failed"}

    data = {"stripeToken": "asdf", "amount": "300", "stripeEmail": "a@a.com"}

    with pytest.raises(ValueError):
        client.post(reverse("charge"), data)
    # post going to #org-running
    assert "channel" not in requests.post.call_args.kwargs.get("json")
    assert "Something went wrong" in requests.post.call_args.kwargs.get("json")["text"]


def test_failed_charge_in_debug_mode(
    client: Client, mocker: object, settings: Settings
) -> None:
    """Verify that a failed charge with Blossom in debug mode uses the debug keys."""
    settings.DEBUG = True
    settings.ENABLE_SLACK = True
    mocker.patch("requests.post")
    mocker.patch("stripe.Charge")
    stripe.Charge.create.return_value = {"status": "failed"}

    data = {"stripeToken": "asdf", "amount": "300", "stripeEmail": "a@a.com"}

    with pytest.raises(ValueError):
        client.post(reverse("charge"), data)
    # post going to #bottest
    assert "channel" in requests.post.call_args.kwargs.get("json")
    assert "Something went wrong" in requests.post.call_args.kwargs.get("json")["text"]
