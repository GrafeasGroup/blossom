import json
import pytest
from unittest.mock import call, patch, PropertyMock, MagicMock

from django_hosts.resolvers import reverse

from blossom.authentication.models import BlossomUser
from blossom.models import Submission
from blossom.slack_conn.helpers import client as slack_client
from blossom.tests.helpers import create_staff_volunteer_with_keys
from blossom.tests.helpers import create_test_submission
from blossom.tests.helpers import create_test_user


class TestSubmissionCreation:
    def test_submission_create(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        data = {"submission_id": "spaaaaace", "source": "the_tests"}
        assert Submission.objects.count() == 0
        result = client.post(
            reverse("submission-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 200
        assert result.json().get("message") == "Post object 1 created!"

        obj = Submission.objects.get(id=1)
        assert obj.submission_id == "spaaaaace"
        assert obj.source == "the_tests"

    def test_submission_create_with_full_args(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        data = {
            "submission_id": "spaaaaace",
            "source": "the_tests",
            "url": "http://example.com",
            "tor_url": "http://example.com/tor",
        }
        assert Submission.objects.count() == 0
        result = client.post(
            reverse("submission-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 200
        obj = Submission.objects.get(id=1)
        assert obj.submission_id == "spaaaaace"
        assert obj.source == "the_tests"
        assert obj.url == "http://example.com"
        assert obj.tor_url == "http://example.com/tor"

    def test_incomplete_submission_create_1(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        data = {
            "submission_id": "spaaaaace",
            # missing source param
        }
        assert Submission.objects.count() == 0
        result = client.post(
            reverse("submission-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 400
        assert result.json().get("result") == "error"
        assert result.json().get("message") == (
            "Must contain the keys `submission_id` (str, 20char max)"
            " and `source` (str 20char max)"
        )

    def test_incomplete_submission_create_2(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        data = {
            # missing submission id
            "source": "the_tests"
        }
        assert Submission.objects.count() == 0
        result = client.post(
            reverse("submission-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 400
        assert result.json().get("result") == "error"
        assert result.json().get("message") == (
            "Must contain the keys `submission_id` (str, 20char max)"
            " and `source` (str 20char max)"
        )


class TestSubmissionMiscEndpoints:
    def test_get_submissions(self, client):
        client, headers = create_staff_volunteer_with_keys(client)

        create_test_submission()

        result = client.get(
            reverse("submission-list", host="api"),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 200
        assert result.json()["results"][0]["submission_id"] == "AAA"

    def test_get_submissions_with_specific_id(self, client):
        client, headers = create_staff_volunteer_with_keys(client)

        # create 2 -- call should only return one
        create_test_submission(s_id="AAA", source="BBB")
        create_test_submission(s_id="CCC", source="DDD")

        result = client.get(
            reverse("submission-list", host="api") + "?submission_id=CCC",
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 200
        assert len(result.json()["results"]) == 1
        assert result.json()["results"][0]["id"] == 2

        # now do a regular call on the same data -- should get both entries
        result = client.get(
            reverse("submission-list", host="api"),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == 200
        assert len(result.json()["results"]) == 2


class TestSubmissionClaimProcess:
    def test_claim(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        create_test_submission()
        data = {"v_username": "janeeyre"}
        result = client.post(
            reverse("submission-claim", host="api", args=[1]),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        v = BlossomUser.objects.first()
        s = Submission.objects.first()
        assert result.status_code == 200
        assert result.json().get("result") == "success"
        assert result.json().get("message") == "Post AAA claimed by janeeyre"
        assert s.claimed_by == v

    def test_claim_wrong_post_id(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        data = {"v_username": "janeeyre"}
        result = client.post(
            reverse("submission-claim", host="api", args=[1]),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 404
        assert result.json().get("message") == "No post with that ID."

    def test_claim_wrong_volunteer_username(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        create_test_submission()
        data = {"v_username": "asdfasdfasdf"}
        result = client.post(
            reverse("submission-claim", host="api", args=[1]),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 404
        assert result.json().get("message") == "No volunteer with that ID / username."

    def test_claim_no_volunteer_info(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        create_test_submission()
        result = client.post(
            reverse("submission-claim", host="api", args=[1]),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 400
        assert result.json().get("message") == (
            "Must give either `v_id` (int, volunteer ID number) or"
            " `v_username` (str, the username of the person you're"
            " looking for) in request json."
    )

    def test_claim_already_claimed(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        guy = create_test_user()

        s = create_test_submission()
        s.claimed_by = BlossomUser.objects.get(id=1)
        s.save()

        data = {"v_id": guy.id}

        result = client.post(
            reverse("submission-claim", host="api", args=[1]),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 409
        assert result.json().get("message") == (
            "Post ID 1 has been claimed already by janeeyre!"
        )


class TestSubmissionDone:

    def test_done_process(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        user = BlossomUser.objects.get(id=1)
        s.claimed_by = user
        s.save()

        data = {"v_id": user.id}

        result = client.post(
            reverse("submission-done", host="api", args=[1]),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 200
        assert result.json().get("message") == "Submission ID AAA completed by janeeyre"

    def test_done_without_claim(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        create_test_submission()
        user = BlossomUser.objects.get(id=1)

        data = {"v_id": user.id}

        result = client.post(
            reverse("submission-done", host="api", args=[1]),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 412
        assert result.json().get("message") == (
            "Submission ID AAA has not yet been claimed!"
        )

    def test_done_without_user_info(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        create_test_submission()

        result = client.post(
            reverse("submission-done", host="api", args=[1]),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 400
        assert result.json().get("message").startswith("Must give either `v_id`")

    def test_done_already_completed(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        s = create_test_submission()
        user = BlossomUser.objects.get(id=1)

        s.claimed_by = user
        s.completed_by = user
        s.save()

        data = {"v_username": user.username}

        result = client.post(
            reverse("submission-done", host="api", args=[1]),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )

        assert result.status_code == 409
        assert result.json().get("message") == (
            "Submission ID AAA has already been completed by janeeyre!"
        )

    @pytest.mark.parametrize(
        "probability,gamma,message,tor_url,trans_url",
        [
            (0.8, 0, False, None, None),
            (0.7999, 50, True, None, None),
            (0.7, 51, False, None, None),
            (0.6999, 100, True, None, None),
            (0.6, 101, False, None, None),
            (0.5999, 250, True, None, None),
            (0.5, 251, False, None, None),
            (0.4999, 500, True, None, None),
            (0.3, 501, False, None, None),
            (0.2999, 1000, True, None, None),
            (0.1, 1001, False, None, None),
            (0.0999, 5000, True, None, None),
            (0.05, 5001, False, None, None),
            (0.0499, 10000, True, None, None),
            (0, 0, True, "url", None),
            (0, 0, True, "tor_url", "trans_url")
        ]
    )
    def test_done_random_checks(self, client, probability, gamma, message, tor_url, trans_url):
        # Mock both the gamma property and the random.random function.
        with patch(
                "blossom.authentication.models.BlossomUser.gamma",
                new_callable=PropertyMock) as mock,\
                patch('random.random', lambda: probability):
            mock.return_value = gamma

            # Mock the Slack client to catch the sent messages by the function under test.
            slack_client.chat_postMessage = MagicMock()
            client, headers = create_staff_volunteer_with_keys(client)
            s = create_test_submission()
            user = BlossomUser.objects.get(id=1)
            if trans_url:
                data = {
                    "submission_id": s.submission_id,
                    "v_id": user.id,
                    "t_id": "ABC",
                    "completion_method": "automated tests",
                    "t_url": trans_url,
                    "t_text": "test content",
                }
                client.post(
                    reverse("transcription-list", host="api"),
                    json.dumps(data),
                    HTTP_HOST="api",
                    content_type="application/json",
                    **headers,
                )

            s.tor_url = tor_url
            s.claimed_by = user
            s.save()

            result = client.post(
                reverse("submission-done", host="api", args=[1]),
                json.dumps({"v_username": user.username}),
                HTTP_HOST="api",
                content_type="application/json",
                **headers,
            )
            slack_message = "Please check the following transcription of u/janeeyre: " \
                            f"{trans_url if trans_url else tor_url}."
            assert result.status_code == 200
            assert result.json().get("message") == "Submission ID AAA completed by janeeyre"
            if message:
                assert call(channel="#transcription_check", text=slack_message)\
                       == slack_client.chat_postMessage.call_args_list[-1]
            else:
                assert slack_client.chat_postMessage.call_count == 0
