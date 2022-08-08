"""Set of tests which are used to validate the behavior of the authentication of users."""
from blossom.authentication.models import BlossomUser
from blossom.utils.test_helpers import create_user

USER_CREATION_DATA = {"username": "Narf"}


def test_get_case_insensitive_usernames() -> None:
    """Test whether `get`s that use usernames are properly case insensitive."""
    create_user(**USER_CREATION_DATA)
    # all four of these should return the same object
    for option in ["nArF", "Narf"]:
        assert BlossomUser.objects.get(username=option)
        assert BlossomUser.objects.get(username__iexact=option)


def test_filter_case_insensitive_usernames() -> None:
    """Test whether `filter`s that use usernames are properly case insensitive."""
    create_user(**USER_CREATION_DATA)
    for option in ["nArF", "Narf"]:
        assert BlossomUser.objects.filter(username=option).count() == 1
        assert BlossomUser.objects.filter(username__iexact=option).count() == 1


def test_verify_usernames_dont_affect_other_filters() -> None:
    """Test that case insensitive usernames don't affect other filters."""
    create_user(**USER_CREATION_DATA)

    for option in ["nArF", "Narf"]:
        for is_vol in [True, False]:
            assert BlossomUser.objects.filter(
                username=option, is_volunteer=is_vol
            ).count() == (1 if is_vol else 0)
            assert BlossomUser.objects.filter(
                username__iexact=option, is_volunteer=is_vol
            ).count() == (1 if is_vol else 0)
