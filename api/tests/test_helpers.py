"""Test the available helper classes and their methods."""
import pytest
from rest_framework import status
from rest_framework.response import Response

from api.helpers import BlossomUserMixin
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
    """Test whether None is returned if no errors nor arguments are passed."""
    result = user_mixin.get_user_from_request(dict())
    assert result is None


def test_wrong_id(user: BlossomUser, user_mixin: BlossomUserMixin) -> None:
    """Test whether None is returned when a nonexistent ID and no errors are passed."""
    result = user_mixin.get_user_from_request({"v_id": user.id + 1})
    assert result is None


def test_wrong_username(user: BlossomUser, user_mixin: BlossomUserMixin) -> None:
    """Test whether None is returned when a wrong username and no errors are passed."""
    result = user_mixin.get_user_from_request({"username": f"{user.username}404"})
    assert result is None


def test_no_parameters_errors(user_mixin: BlossomUserMixin) -> None:
    """Test whether a 400 Response is returned when no arguments are passed."""
    result = user_mixin.get_user_from_request(dict(), errors=True)
    assert isinstance(result, Response)
    assert result.status_code == status.HTTP_400_BAD_REQUEST


def test_wrong_id_errors(user: BlossomUser, user_mixin: BlossomUserMixin) -> None:
    """Test whether a 404 Response is returned when an invalid ID is passed."""
    result = user_mixin.get_user_from_request({"v_id": user.id + 1}, errors=True)
    assert isinstance(result, Response)
    assert result.status_code == status.HTTP_404_NOT_FOUND


def test_wrong_username_errors(user: BlossomUser, user_mixin: BlossomUserMixin) -> None:
    """Test whether a 404 Response is returned when an invalid username is passed."""
    result = user_mixin.get_user_from_request(
        {"username": f"{user.username}404"}, errors=True
    )
    assert isinstance(result, Response)
    assert result.status_code == status.HTTP_404_NOT_FOUND
