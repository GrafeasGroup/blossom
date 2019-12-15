import pytest

from blossom.management.commands import bootstrap

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass


@pytest.fixture()
def setup_site():
    bootstrap.Command().handle()
