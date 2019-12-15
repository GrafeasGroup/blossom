from types import SimpleNamespace


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
