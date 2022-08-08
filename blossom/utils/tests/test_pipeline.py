from blossom.utils.pipeline import load_user
from blossom.utils.test_helpers import create_user


class BaseAuth:
    name = "reddit"


def test_load_user_with_valid_username() -> None:
    """Verify that a valid username returns a valid user to the pipeline."""
    user = create_user(username="abc")
    assert load_user(BaseAuth, details={"username": "abc"}) == {"user": user}


def test_load_user_with_wrong_case_username() -> None:
    """Verify that it still works with improper casing."""
    user = create_user(username="abc")
    assert load_user(BaseAuth, details={"username": "ABC"}) == {"user": user}


def test_load_user_with_invalid_username() -> None:
    """Verify that passing the wrong username will not return a user."""
    assert load_user(BaseAuth, details={"username": "abc"}) is None


def test_load_user_with_invalid_backend() -> None:
    """Verify that any other backend will not return a user."""
    create_user(username="abc")
    baseauth = BaseAuth()
    baseauth.name = "asdf"
    assert load_user(baseauth, details={"username": "abc"}) is None
