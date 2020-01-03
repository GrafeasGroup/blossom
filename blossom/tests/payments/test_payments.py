import json

from django_hosts.resolvers import reverse

import requests
import stripe
import pytest


def test_payment_endpoint_with_get_request(client):
    result = client.get(reverse("charge", host="payments"), HTTP_HOST="payments")
    assert result.status_code == 200
    assert result.content == b"go away"


def test_payment_endpoint(client, mocker, setup_site):
    mocker.patch("requests.post")
    mocker.patch("stripe.Charge")
    stripe.Charge.create.return_value = {"status": "succeeded"}

    data = {"stripeToken": "asdf", "amount": "300", "stripeEmail": "a@a.com"}

    result = client.post(reverse("charge", host="payments"), data, HTTP_HOST="payments")
    assert result.status_code == 302
    assert "thank-you" in result.url
    requests.post.assert_called_once()
    assert "live" in stripe.api_key
    stripe.Charge.create.assert_called_once()
    # post going to #org-running
    assert "channel" not in requests.post.call_args.kwargs.get("json")


def test_payment_endpoint_debug_mode(client, mocker, setup_site, settings):
    settings.DEBUG = True
    mocker.patch("requests.post")
    mocker.patch("stripe.Charge")
    stripe.Charge.create.return_value = {"status": "succeeded"}

    data = {"stripeToken": "asdf", "amount": "300", "stripeEmail": "a@a.com"}

    result = client.post(reverse("charge", host="payments"), data, HTTP_HOST="payments")

    requests.post.assert_called_once()
    assert "test" in stripe.api_key
    stripe.Charge.create.assert_called_once()
    # post going to #org-running
    assert "channel" in requests.post.call_args.kwargs.get("json")


def test_failed_charge(client, mocker):
    mocker.patch("requests.post")
    mocker.patch("stripe.Charge")
    stripe.Charge.create.return_value = {"status": "failed"}

    data = {"stripeToken": "asdf", "amount": "300", "stripeEmail": "a@a.com"}

    with pytest.raises(ValueError):
        result = client.post(
            reverse("charge", host="payments"), data, HTTP_HOST="payments"
        )
    # post going to #org-running
    assert "channel" not in requests.post.call_args.kwargs.get("json")
    assert "Something went wrong" in requests.post.call_args.kwargs.get("json")["text"]


def test_failed_charge_in_debug_mode(client, mocker, settings):
    settings.DEBUG = True
    mocker.patch("requests.post")
    mocker.patch("stripe.Charge")
    stripe.Charge.create.return_value = {"status": "failed"}

    data = {"stripeToken": "asdf", "amount": "300", "stripeEmail": "a@a.com"}

    with pytest.raises(ValueError):
        result = client.post(
            reverse("charge", host="payments"), data, HTTP_HOST="payments"
        )
    # post going to #bottest
    assert "channel" in requests.post.call_args.kwargs.get("json")
    assert "Something went wrong" in requests.post.call_args.kwargs.get("json")["text"]
