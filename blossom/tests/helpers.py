from types import SimpleNamespace

from blossom.authentication.models import BlossomUser

guy = SimpleNamespace(
    username="guymontag",
    email="gmontag@firehouse451.utility",
    password="137'58u2n17up",
)

jane = SimpleNamespace(
    username="janeeyre", email="miltonsux@bl.uk", password="20ch35732"
)


def create_test_user(
    user_info: dict = None,
    superuser: bool = False,
    is_volunteer: bool = True,
    is_grafeas_staff: bool = False,
) -> BlossomUser:
    """Create a configurable test user."""
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
