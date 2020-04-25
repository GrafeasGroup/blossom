from types import SimpleNamespace
from typing import Tuple, Dict, Union

from api.models import Submission
from authentication.models import BlossomUser, APIKey

guy = SimpleNamespace(
    username="guymontag",
    email="gmontag@firehouse451.utility",
    password="137'58u2n17up",
)

jane = SimpleNamespace(
    username="janeeyre", email="miltonsux@bl.uk", password="20ch35732"
)


def create_test_user(
    user_info=None, superuser=False, is_volunteer=True, is_grafeas_staff=False
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
