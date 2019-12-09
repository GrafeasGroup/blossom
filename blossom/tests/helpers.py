from types import SimpleNamespace


guy = SimpleNamespace(
    username="GuyMontag",
    email="gmontag@firehouse451.utility",
    password="137'58u2n17up",
)


def create_test_user(usermodel):
    user, created = usermodel.objects.get_or_create(
        username=guy.username, email=guy.email)
    user.set_password(guy.password)
    user.save()
    return user
