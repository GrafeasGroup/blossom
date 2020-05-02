"""Test the available helper classes and their methods."""
from types import SimpleNamespace
from typing import Dict, Set

import pytest
from django.shortcuts import Http404
from rest_framework import serializers

from api.helpers import BlossomUserMixin, validate_request
from api.tests.helpers import create_user
from authentication.models import BlossomUser


@pytest.fixture
def user() -> BlossomUser:
    """Pytest fixture to create the standard user before each test."""
    return create_user()


@pytest.fixture
def user_mixin() -> BlossomUserMixin:
    """Pytest fixture to create the BlossomUserMixin before each test."""
    return BlossomUserMixin()


def test_id_retrieval(user: BlossomUser, user_mixin: BlossomUserMixin) -> None:
    """Test whether the user is correctly retrieved with the user's ID."""
    result = user_mixin.get_user_from_request({"v_id": user.id})
    assert result == user


def test_username_retrieval(user: BlossomUser, user_mixin: BlossomUserMixin) -> None:
    """Test whether the user is correctly retrieved with the user's name."""
    result = user_mixin.get_user_from_request({"username": user.username})
    assert result == user


def test_combined_retrieval(user: BlossomUser, user_mixin: BlossomUserMixin) -> None:
    """Test whether the user is retrieved when both the ID and username is included."""
    result = user_mixin.get_user_from_request(
        {"username": user.username, "v_id": user.id}
    )
    assert result == user


def test_no_parameters(user_mixin: BlossomUserMixin) -> None:
    """Test whether a 400 Response is returned when no arguments are passed."""
    with pytest.raises(serializers.ValidationError):
        user_mixin.get_user_from_request(dict())


def test_wrong_id(user: BlossomUser, user_mixin: BlossomUserMixin) -> None:
    """Test whether a 404 Response is returned when an invalid ID is passed."""
    with pytest.raises(Http404):
        user_mixin.get_user_from_request({"v_id": user.id + 1})


def test_wrong_username(user: BlossomUser, user_mixin: BlossomUserMixin) -> None:
    """Test whether a 404 Response is returned when an invalid username is passed."""
    with pytest.raises(Http404):
        user_mixin.get_user_from_request({"username": f"{user.username}404"})


@pytest.mark.parametrize(
    "data,data_params,query,query_params,raises",
    [
        ({"a": "a", "b": "b"}, {"a"}, dict(), set(), False),
        (dict(), set(), {"a": "a", "b": "b"}, {"a"}, False),
        ({"a": "a"}, {"a"}, {"b": "b"}, {"b"}, False),
        (dict(), {"a"}, dict(), set(), True),
        (dict(), set(), dict(), {"a"}, True),
    ],
)
def test_validate_request(
    data: Dict, data_params: Set, query: Dict, query_params: Set, raises: bool
) -> None:
    """
    Test whether the behavior of the validate_request decorator is as documented.

    This is done by creating a simple object with the same fields as a Request
    and passing this to a test function wrapped with the decorator. If an error
    has to be thrown, this is asserted and otherwise it is asserted whether
    only and all required values are passed as kwargs with the correct
    corresponding values.
    """

    @validate_request(query_params=query_params, data_params=data_params)
    def test_function(*args: object, **kwargs: object) -> None:
        assert all(param in kwargs for param in data_params.union(query_params))
        assert all(key in data_params.union(query_params) for key in kwargs.keys())
        assert all(data[param] == kwargs[param] for param in data_params)
        assert all(query[param] == kwargs[param] for param in query_params)

    request = SimpleNamespace(data=data, query_params=query)
    if raises:
        with pytest.raises(serializers.ValidationError):
            test_function(None, request)
    else:
        test_function(None, request)
