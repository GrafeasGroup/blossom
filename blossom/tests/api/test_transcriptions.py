import json

from django_hosts.resolvers import reverse

from blossom.authentication.models import BlossomUser
from blossom.models import Submission, Transcription
from blossom.tests.helpers import (
    create_test_user,
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
        assert result.status_code == 200
        assert (
            result.json().get("message")
            == "Transcription ID 1 created on post AAA, written by janeeyre"
        )
        assert result.json()['data']['id'] == 1

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
        assert result.status_code == 200
        assert (
            result.json().get("message")
            == "Transcription ID 1 created on post AAA, written by janeeyre"
        )

        obj = Transcription.objects.get(id=1)
        assert obj.submission == s
        assert obj.text == None
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
        assert result.status_code == 200
        assert (
            result.json().get("message")
            == "Transcription ID 1 created on post AAA, written by janeeyre"
        )

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
        assert result.status_code == 400
        assert result.json().get("message") == (
            "Missing data body key `submission_id`, str; the ID of the post"
            " the transcription is on."
        )

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
        assert result.status_code == 404
        assert result.json().get("message") == "No post found with ID 999!"

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
        assert result.status_code == 404
        assert (
            result.json().get("message") == "No volunteer found with that ID / username."
        )

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
        assert result.status_code == 400
        assert (
            result.json().get("message")
            == "Missing data body key `t_id`, str; the ID of the transcription."
        )

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
        assert result.status_code == 400
        assert result.json().get("message") == (
            "Missing data body key `completion_method`, str; the service this"
            " transcription was completed through. `app`, `ToR`, etc. 20char max."
        )

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
        assert result.status_code == 400
        assert result.json().get("message") == (
            "Missing data body key `t_url`, str; the direct URL for the"
            " transcription. Use string `None` if no URL is available."
        )

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
        assert result.status_code == 400
        assert result.json().get("message") == (
            "Missing data body key `t_text`, str; the content of the transcription."
        )

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
        assert result.status_code == 400
        assert result.json().get("message") == (
            "Received both t_text and ocr_text -- must be one or the other."
        )


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
        assert result.status_code == 200
        assert (
                result.json().get("message")
                == "Found the folowing transcriptions for requested ID AAA."
        )

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

        assert result.status_code == 200
        assert result.json().get('message').startswith("Did not find any transcriptions")

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

        assert result.status_code == 400
        assert result.json().get('message').startswith("This endpoint only supports")


def test_random_transcription_for_review(client):
    client, headers = create_staff_volunteer_with_keys(client)
    s = create_test_submission()
    v = BlossomUser.objects.first()

    result = client.get(
        reverse("transcription-review-random", host="api"),
        HTTP_HOST="api",
        **headers,
    )

    assert result.json().get('message') == 'No available transcriptions to review.'
    assert result.status_code == 200
    assert result.json().get('data') is None

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

    assert result.json().get('data') is not None
    assert result.json().get('data').get('submission') is not None
    assert result.status_code == 200
