from typing import Dict, Tuple

from django.test import Client
from social_django.models import UserSocialAuth

from blossom.api.models import Source, Submission, Transcription, TranscriptionCheck
from blossom.authentication.models import APIKey, BlossomUser

BASE_SUBMISSION_INFO = {
    "original_id": "base_original_id",
    "source": None,
}
BASE_TRANSCRIPTION_INFO = {
    "original_id": "base_original_id",
    "source": None,
    "url": "https://baseurl.org",
    "text": "base_text",
    "removed_from_reddit": False,
}
BASE_USER_INFO = {
    "username": "base_username",
    "email": "base_email",
    "password": "base_password",
    "is_staff": True,
    "is_grafeas_staff": True,
    "is_volunteer": True,
    "api_key": None,
    "accepted_coc": True,
}
BASE_SOCIAL_AUTH_INFO = {
    "provider": "reddit",
    "uid": "12345abc",
    "extra_data": {"refresh_token": "aaa"},
}


def create_user(**kwargs: object) -> BlossomUser:
    """
    Create a new user or get the user with the corresponding user information.

    The user which is created has default fields corresponding to the "BASE_USER_INFO"
    constant. Any attribute of this constant can be overwritten by providing the attribute
    with its desired value as a keyword argument (e.g. providing username="test" will
    result in the returned user to have the username "test").

    :param kwargs: The desired change of fields of the submission compared to the user
    :returns: The created user
    """
    user_info = {
        **BASE_USER_INFO,
        **{key: kwargs[key] for key in kwargs if key in dir(BlossomUser)},
    }
    user, _ = BlossomUser.objects.get_or_create(**user_info)
    return user


def get_default_test_source(override: str = None) -> Source:
    """Build or get the Source needed to create transcriptions / submissions."""
    source, _ = Source.objects.get_or_create(
        name="unit_tests" if not override else override
    )
    return source


def create_submission(**kwargs: object) -> Submission:
    """
    Create a new submission or get the submission with the corresponding information.

    The submission which is created has default fields corresponding to the
    "BASE_SUBMISSION_INFO" constant. Any attribute of this constant can be
    overwritten by providing the attribute with its desired value as a keyword
    argument (e.g. providing source="test" will result in the returned
    submission to have the source "test").


    :param kwargs: The desired change of fields of the submission compared to the default
    :returns: The created submission
    """
    submission_info = {
        **BASE_SUBMISSION_INFO,
        **{key: kwargs[key] for key in kwargs if key in dir(Submission)},
    }
    if submission_info["source"] is None:
        submission_info["source"] = get_default_test_source()
    if isinstance(submission_info["source"], str):
        submission_info["source"] = Source.objects.get(name=submission_info["source"])
    return Submission.objects.create(**submission_info)


def create_transcription(
    submission: Submission, user: BlossomUser, **kwargs: object
) -> Transcription:
    """
    Create a new submission or get the submission with the corresponding information.

    The submission which is created has default fields corresponding to the
    "BASE_SUBMISSION_INFO" constant. Any attribute of this constant can be
    overwritten by providing the attribute with its desired value as a keyword
    argument (e.g. providing source="test" will result in the returned
    submission to have the source "test").

    :param submission: The Submission to which the transcription belongs
    :param user: The BlossomUser that authored this Transcription
    :param kwargs: The desired change of fields of the submission compared to the default
    :returns: The created transcription
    """
    transcription_info = {
        **BASE_TRANSCRIPTION_INFO,
        **{key: kwargs[key] for key in kwargs if key in dir(Transcription)},
        "submission": submission,
        "author": user,
    }
    if transcription_info["source"] is None:
        transcription_info["source"] = get_default_test_source()
    return Transcription.objects.create(**transcription_info)


def create_check(transcription: Transcription, **kwargs: object) -> TranscriptionCheck:
    """Create a new check for the given transcription.

    :param transcription: The transcription to create the check for.
    :param kwargs: The desired change of fields of the check compared to the default.
    :returns: The created transcription check
    """
    check_info = {
        "trigger": "Test",
        "transcription": transcription,
        **kwargs,
    }
    return TranscriptionCheck.objects.create(**check_info)


def setup_user_client(
    client: Client, login: bool = True, **kwargs: object
) -> Tuple[Client, Dict, BlossomUser]:
    """
    Set the client up with a new user, forcing login on the client as a default.

    The user will be created as to the "BASE_USER_INFO" specification. Any
    desired changes to this user can be provided as a keyword argument to this
    function.

    :param client: The client to set up
    :param login: Whether to login the client with the user or not
    :param kwargs: The desired change of fields of the user compared to the default
    :returns: The client, the HTTP header with the API key, and the created user
    """
    api_key, key = APIKey.objects.create_key(name="base_api_key")
    user = create_user(api_key=api_key, **kwargs)
    if login:
        client.force_login(user)
    return client, {"HTTP_AUTHORIZATION": f"Api-Key {key}"}, user


def add_social_auth_to_user(user: BlossomUser) -> None:
    """Add a social auth object to the attached user."""
    social_info = {"user": user, **BASE_SOCIAL_AUTH_INFO}
    return UserSocialAuth.objects.create(**social_info)
