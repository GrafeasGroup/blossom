import json

from django_hosts.resolvers import reverse

from blossom.authentication.models import BlossomUser
from blossom.models import Submission
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
        assert result.json() == {"success": "Post object 1 created!"}

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
        assert result.json() == {
            "error": "Must contain the keys `submission_id` (str, 20char max)"
            " and `source` (str 20char max)"
        }

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
        assert result.json() == {
            "error": "Must contain the keys `submission_id` (str, 20char max)"
            " and `source` (str 20char max)"
        }


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
        assert result.json() == {"success": "Post AAA claimed by janeeyre"}
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
        assert result.json() == {"error": "No post with that ID."}

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
        assert result.json() == {"error": "No volunteer with that ID / username."}

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
        assert result.json() == {
            "error": "Must give either `v_id` (int, volunteer ID number) or"
            " `v_username` (str, the username of the person you're"
            " looking for) in request json."
        }

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
        assert result.json() == {
            "error": "Post ID 1 has been claimed already by janeeyre!"
        }


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
        assert result.json() == {"success": "Submission ID AAA completed by janeeyre"}

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
        assert result.json() == {"error": "Submission ID AAA has not yet been claimed!"}

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
        assert result.json().get("error").startswith("Must give either `v_id`")

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
        assert result.json() == {
            "error": "Submission ID AAA has already been completed by janeeyre!"
        }
