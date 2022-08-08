from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import PropertyMock, patch

import pytest
import pytz
from django.test import Client

from blossom.utils.test_helpers import (
    create_submission,
    create_transcription,
    setup_user_client,
)


def test_gamma(client: Client) -> None:
    """Test that a user's gamma is calculated correctly."""
    client, headers, user = setup_user_client(client, id=123, username="Test")

    times = [
        datetime(2022, 3, 1),
        datetime(2022, 3, 3),
        datetime(2022, 4, 1),
        datetime(2022, 5, 13),
    ]

    # Create the user's transcriptions
    for time in times:
        submission = create_submission(
            create_time=time - timedelta(days=2),
            claimed_by=user,
            claim_time=time - timedelta(days=1),
            completed_by=user,
            complete_time=time,
        )
        create_transcription(submission=submission, user=user, create_time=time)

    assert user.gamma == 4


def test_gamma_with_empty_times(client: Client) -> None:
    """Make sure that the gamma works even if some times are missing.

    Some older dummy submissions might not have the claim_time or create_time
    fields set. We need to make sure that the gamma still includes them until
    we fix the data.
    """
    client, headers, user = setup_user_client(client, id=123, username="Test")

    times = [
        None,
        datetime(2022, 3, 1),
        datetime(2022, 3, 3),
        None,
        datetime(2022, 4, 1),
        datetime(2022, 5, 13),
    ]

    # Create the user's transcriptions
    for time in times:
        submission = create_submission(
            create_time=time or datetime.now(),
            claimed_by=user,
            claim_time=time,
            completed_by=user,
            complete_time=time,
        )
        create_transcription(
            submission=submission, user=user, create_time=time or time or datetime.now()
        )

    assert user.gamma == 6


@pytest.mark.parametrize(
    "start_time, end_time, expected",
    [
        (None, None, 4),
        (datetime(2022, 3, 1), datetime(2022, 5, 13), 4),
        (None, datetime(2022, 3, 13), 2),
        (datetime(2022, 3, 2), None, 3),
        (datetime(2022, 3, 2), datetime(2022, 3, 12), 1),
        (datetime(2023, 1, 1), None, 0),
        (None, datetime(2021, 1, 1), 0),
    ],
)
def test_gamma_at_time(
    client: Client,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    expected: int,
) -> None:
    """Test that the gamma is calculated correctly for a time frame."""
    client, headers, user = setup_user_client(client, id=123, username="Test")

    times = [
        datetime(2022, 3, 1),
        datetime(2022, 3, 3),
        datetime(2022, 4, 1),
        datetime(2022, 5, 13),
    ]

    # Create the user's transcriptions
    for time in times:
        submission = create_submission(
            create_time=time - timedelta(days=2),
            claimed_by=user,
            claim_time=time - timedelta(days=1),
            completed_by=user,
            complete_time=time,
        )
        create_transcription(submission=submission, user=user, create_time=time)

    actual = user.gamma_at_time(start_time=start_time, end_time=end_time)
    assert actual == expected


@pytest.mark.parametrize(
    "recent_gamma, total_gamma, expected",
    [(0, 10000, True), (10, 10000, True), (11, 11, False), (15, 10000, False)],
)
def test_has_low_activity(
    client: Client,
    recent_gamma: int,
    total_gamma: int,
    expected: bool,
) -> None:
    """Test whether low transcribing activity is determined correctly."""
    # Mock the total gamma
    with patch(
        "blossom.authentication.models.BlossomUser.gamma",
        new_callable=PropertyMock,
        return_value=total_gamma,
    ):
        client, headers, user = setup_user_client(client)
        now = datetime.now(tz=pytz.UTC)

        # Create the recent transcriptions
        for i in range(0, recent_gamma):
            submission = create_submission(
                id=i + 100,
                claimed_by=user,
                completed_by=user,
                complete_time=now,
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
    client: Client,
    total_gamma: int,
    expected: float,
) -> None:
    """Test whether the automatic check percentage is calculated correctly."""
    client, headers, user = setup_user_client(client)

    # Mock the total gamma
    with patch(
        "blossom.authentication.models.BlossomUser.gamma",
        new_callable=PropertyMock,
        return_value=total_gamma,
    ):
        assert user.auto_check_percentage == expected


@pytest.mark.parametrize(
    "total_gamma, overwrite_percentage, expected",
    [(100, None, 0.3), (100, 0.8, 0.8), (300, None, 0.05), (300, 0.7, 0.7)],
)
def test_check_percentage(
    client: Client,
    total_gamma: int,
    overwrite_percentage: Optional[float],
    expected: float,
) -> None:
    """Test whether the automatic check percentage is calculated correctly."""
    client, headers, user = setup_user_client(
        client, overwrite_check_percentage=overwrite_percentage
    )

    # Mock the total gamma
    with patch(
        "blossom.authentication.models.BlossomUser.gamma",
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
        "blossom.authentication.models.BlossomUser.has_low_activity",
        new_callable=PropertyMock,
        return_value=has_low_activity,
    ), patch(
        "blossom.authentication.models.BlossomUser.check_percentage",
        new_callable=PropertyMock,
        return_value=check_percentage,
    ), patch(
        "random.random", lambda: random_value
    ):
        assert user.should_check_transcription() == expected


@pytest.mark.parametrize(
    "has_low_activity, overwrite, check_percentage, expected",
    [
        (True, True, 1.0, "Low activity"),
        (False, True, 0.7, "Watched (70.0%)"),
        (False, False, 0.3, "Automatic (30.0%)"),
    ],
)
def test_transcription_check_reason(
    client: Client,
    has_low_activity: bool,
    overwrite: bool,
    check_percentage: float,
    expected: str,
) -> None:
    """Test whether the check reason is determined correctly."""
    overwrite_check_percentage = check_percentage if overwrite else None
    client, headers, user = setup_user_client(
        client, overwrite_check_percentage=overwrite_check_percentage
    )

    # Patch all relevant properties
    with patch(
        "blossom.authentication.models.BlossomUser.has_low_activity",
        new_callable=PropertyMock,
        return_value=has_low_activity,
    ), patch(
        "blossom.authentication.models.BlossomUser.check_percentage",
        new_callable=PropertyMock,
        return_value=check_percentage,
    ):
        assert user.transcription_check_reason() == expected
