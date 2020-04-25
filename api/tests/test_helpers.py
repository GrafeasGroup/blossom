"""Test the available helper classes and their methods."""
from api.helpers import VolunteerMixin
from api.tests.helpers import create_user


def test_volunteer_mixin_get_username() -> None:
    """Test whether the Volunteer Mixin provides the correct user given an username."""
    user = create_user()
    assert VolunteerMixin().get_volunteer(username=user.username) == user


# TODO: Add more tests for the remaining scenarios for both helper classes.
