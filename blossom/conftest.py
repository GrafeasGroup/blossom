from typing import Any

import pytest
from pytest_django.fixtures import SettingsWrapper

from blossom.management.commands import bootstrap_site


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db: Any) -> None:
    """Give all tests database access."""
    pass


@pytest.fixture(autouse=True)
def enable_app(settings: SettingsWrapper) -> None:
    """Run all the tests for the transcription app even if it's not enabled."""
    settings.ENABLE_APP = True


@pytest.fixture(autouse=True)
def setup_site() -> None:
    """Fixture that configures the site as if it were about to be deployed."""
    bootstrap_site.Command().handle()
