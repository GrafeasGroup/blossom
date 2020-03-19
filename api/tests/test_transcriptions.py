import json

from django_hosts.resolvers import reverse
from rest_framework import status

from api.models import Transcription
from authentication.models import BlossomUser
from blossom.tests.helpers import (
    create_staff_volunteer_with_keys,
    create_test_submission,
)


class TestTranscriptionCreation:
    def test_transcription_create(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        v = BlossomUser.objects.first()
        data = {
            "submission_id": s.submission_id,
            "v_id": v.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
        }
        assert Transcription.objects.count() == 0
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_201_CREATED
        assert result.json()['id'] == 1

        obj = Transcription.objects.get(id=1)
        assert obj.submission == s
        assert obj.completion_method == "automated tests"
        assert obj.author == v
        assert obj.transcription_id == "ABC"
        assert obj.url == "https://example.com"
        assert obj.text == "test content"

    def test_transcription_create_ocr_text(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        v = BlossomUser.objects.first()
        # this data comes from tor_ocr and does not have the t_text key
        data = {
            "submission_id": s.submission_id,
            "v_id": v.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "ocr_text": "test content",
        }
        assert Transcription.objects.count() == 0
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_201_CREATED

        obj = Transcription.objects.get(id=1)
        assert obj.submission == s
        assert obj.text is None
        assert obj.ocr_text == "test content"

    def test_transcription_create_alt_submission_id(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        v = BlossomUser.objects.first()
        data = {
            "submission_id": s.id,
            "v_id": v.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_201_CREATED

    def test_transcription_no_submission_id(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        create_test_submission()
        v = BlossomUser.objects.first()
        data = {
            "v_id": v.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_transcription_with_invalid_submission_id(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        create_test_submission()
        v = BlossomUser.objects.first()
        data = {
            "submission_id": 999,
            "v_id": v.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_404_NOT_FOUND

    def test_transcription_with_invalid_volunteer_id(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        data = {
            "submission_id": s.submission_id,
            "v_id": 999,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_404_NOT_FOUND

    def test_transcription_with_missing_transcription_id(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        v = BlossomUser.objects.first()
        data = {
            "submission_id": s.submission_id,
            "v_id": v.id,
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_transcription_with_missing_completion_method(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        v = BlossomUser.objects.first()
        data = {
            "submission_id": s.submission_id,
            "v_id": v.id,
            "t_id": "ABC",
            "t_url": "https://example.com",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_transcription_with_missing_transcription_url(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        v = BlossomUser.objects.first()
        data = {
            "submission_id": s.submission_id,
            "v_id": v.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_text": "test content",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_transcription_with_missing_transcription_text(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        v = BlossomUser.objects.first()
        data = {
            "submission_id": s.submission_id,
            "v_id": v.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_transcription_with_t_text_and_ocr_text(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        v = BlossomUser.objects.first()
        data = {
            "submission_id": s.submission_id,
            "v_id": v.id,
            "t_id": "ABC",
            "completion_method": "automated tests",
            "t_url": "https://example.com",
            "t_text": "test content",
            "ocr_text": "ocr content"
        }
        result = client.post(
            reverse("transcription-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST


class TestTranscriptionSearch(object):
    def test_transcription_search(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        v = BlossomUser.objects.first()
        t = Transcription.objects.create(
            submission=s,
            author=v,
            transcription_id='ABC',
            completion_method='tests'
        )

        result = client.get(
            reverse("transcription-search", host="api") + "?submission_id=AAA",
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == status.HTTP_200_OK

    def test_transcription_search_wrong_id(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        v = BlossomUser.objects.first()

        result = client.get(
            reverse("transcription-search", host="api") + "?submission_id=ZZZ",
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_200_OK
        assert not result.json()

    def test_transcription_search_no_submission_id(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        v = BlossomUser.objects.first()

        result = client.get(
            reverse("transcription-search", host="api"),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == status.HTTP_400_BAD_REQUEST


def test_random_transcription_for_review(client):
    client, headers = create_staff_volunteer_with_keys(client)
    s = create_test_submission()
    v = BlossomUser.objects.first()

    result = client.get(
        reverse("transcription-review-random", host="api"),
        HTTP_HOST="api",
        **headers,
    )

    assert not result.content
    assert result.status_code == status.HTTP_200_OK

    t = Transcription.objects.create(
        submission=s,
        author=v,
        transcription_id='ABC',
        completion_method='tests'
    )

    result = client.get(
        reverse("transcription-review-random", host="api"),
        HTTP_HOST="api",
        **headers,
    )

    assert result.json().get('submission') is not None
    assert result.status_code == status.HTTP_200_OK
