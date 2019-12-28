from types import SimpleNamespace
from typing import Tuple, Dict

from blossom.authentication.models import BlossomUser, APIKey


guy = SimpleNamespace(
    username="guymontag",
    email="gmontag@firehouse451.utility",
    password="137'58u2n17up",
)

jane = SimpleNamespace(
    username="janeeyre",
    email="miltonsux@bl.uk",
    password="20ch35732"
)


def create_test_user(
        user_info=None,
        superuser=False,
        is_volunteer=True,
        is_grafeas_staff=False
):
    if not user_info:
        user_info = guy

    user, _ = BlossomUser.objects.get_or_create(
        username=user_info.username,
        email=user_info.email,
        is_staff=superuser,
        is_grafeas_staff=is_grafeas_staff,
        is_volunteer=is_volunteer,
    )
    user.set_password(guy.password)
    user.save()
    return user


def create_volunteer(with_api_key: bool=False) -> Tuple[BlossomUser, Dict[str, str]]:
    """
    Usage:

    v = create_volunteer()
    OR
    v, headers = create_volunteer(with_api_key=True)

    :param with_api_key: bool
    :return:
    """
    v = create_test_user(user_info=jane)
    v.set_password(jane.password)
    v.save()

    if with_api_key:
        api_key, key = APIKey.objects.create_key(name="jane")
        v.api_key = api_key
        v.save()
        # preformat the headers
        return v, {"HTTP_X_API_KEY": key}

    return v


def create_staff_volunteer_with_keys(client):
    v, headers = create_volunteer(with_api_key=True)
    v.is_grafeas_staff = True
    v.save()
    client.force_login(v)

    return client, headers
