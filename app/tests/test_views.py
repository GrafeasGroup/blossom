# flake8: noqa

from django.test import Client

from app.views import (
    TranscribeSubmission,
    accept_coc,
    choose_transcription,
    unclaim_submission,
)


def test_accept_coc(client: Client) -> None:
    ...
