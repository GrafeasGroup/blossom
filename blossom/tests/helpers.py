from types import SimpleNamespace
from typing import Tuple, Dict

from blossom.api.models import Volunteer, APIKey


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


def create_test_user(usermodel, superuser=False):
    user, _ = usermodel.objects.get_or_create(
        username=guy.username, email=guy.email, is_staff=superuser
    )
    user.set_password(guy.password)
    user.save()
    return user


def create_volunteer(with_api_key: bool=False) -> Tuple[Volunteer, Dict[str, str]]:
    """
    Usage:

    v = create_volunteer()
    OR
    v, headers = create_volunteer(with_api_key=True)

    :param with_api_key: bool
    :return:
    """
    v = Volunteer.objects.create(username=jane.username)
    v.set_password(jane.password)
    v.save()

    if with_api_key:
        api_key, key = APIKey.objects.create_key(name="jane")
        v.api_key = api_key
        v.save()
        # preformat the headers
        return v, {"HTTP_X_API_KEY": key}

    return v
