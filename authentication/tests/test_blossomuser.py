from datetime import datetime
from typing import Optional
from unittest.mock import PropertyMock, patch

import pytest
import pytz
from django.test import Client

from utils.test_helpers import (
    create_submission,
    create_transcription,
    setup_user_client,
)


@pytest.mark.parametrize(
    "recent_gamma, total_gamma, expected",
    [(0, 10000, True), (5, 10000, True), (6, 6, False), (10, 10000, False)],
)
def test_has_low_activity(
    client: Client, recent_gamma: int, total_gamma: int, expected: bool,
) -> None:
    """Test whether low transcribing activity is determined correctly."""
    # Mock the total gamma
    with patch(
        "authentication.models.BlossomUser.gamma",
        new_callable=PropertyMock,
        return_value=total_gamma,
    ):
        client, headers, user = setup_user_client(client)
        now = datetime.now(tz=pytz.UTC)

        # Create the recent transcriptions
        for i in range(0, recent_gamma):
            submission = create_submission(
                id=i + 100, claimed_by=user, completed_by=user, complete_time=now,
            )
            create_transcription(submission, user, id=i + 100, create_time=now)

        assert user.has_low_activity == expected


@pytest.mark.parametrize(
    "total_gamma, expected",
    [
        (0, 1.0),
        (10, 1.0),
        (11, 0.5),
        (50, 0.5),
        (100, 0.3),
        (250, 0.15),
        (300, 0.05),
        (5000, 0.01),
        (5001, 0.005),
    ],
)
def test_auto_check_percentage(
    client: Client, total_gamma: int, expected: float,
) -> None:
    """Test whether the automatic check percentage is calculated correctly."""
    client, headers, user = setup_user_client(client)

    # Mock the total gamma
    with patch(
        "authentication.models.BlossomUser.gamma",
        new_callable=PropertyMock,
        return_value=total_gamma,
    ):
        assert user.auto_check_percentage == expected


@pytest.mark.parametrize(
    "total_gamma, override_percentage, expected",
    [(100, None, 0.3), (100, 0.8, 0.8), (300, None, 0.05), (300, 0.7, 0.7)],
)
def test_check_percentage(
    client: Client,
    total_gamma: int,
    override_percentage: Optional[float],
    expected: float,
) -> None:
    """Test whether the automatic check percentage is calculated correctly."""
    client, headers, user = setup_user_client(
        client, overwrite_check_percentage=override_percentage
    )

    # Mock the total gamma
    with patch(
        "authentication.models.BlossomUser.gamma",
        new_callable=PropertyMock,
        return_value=total_gamma,
    ):
        assert user.check_percentage == expected


@pytest.mark.parametrize(
    "has_low_activity, check_percentage, random_value, expected",
    [
        (True, 0, 1, True),
        (False, 0.8, 0.8, True),
        (False, 0.8, 0.5, True),
        (False, 0.8, 0.81, False),
    ],
)
def test_should_check_transcription(
    client: Client,
    has_low_activity: bool,
    check_percentage: float,
    random_value: float,
    expected: bool,
) -> None:
    """Test whether the checks are determined correctly."""
    client, headers, user = setup_user_client(client)

    # Patch all relevant properties
    with patch(
        "authentication.models.BlossomUser.has_low_activity",
        new_callable=PropertyMock,
        return_value=has_low_activity,
    ), patch(
        "authentication.models.BlossomUser.check_percentage",
        new_callable=PropertyMock,
        return_value=check_percentage,
    ), patch(
        "random.random", lambda: random_value
    ):
        assert user.should_check_transcription() == expected
