import json

from django_hosts.resolvers import reverse

from blossom.authentication.models import BlossomUser
from blossom.models import Transcription, Submission
from blossom.tests.helpers import create_volunteer, create_staff_volunteer_with_keys


class TestVolunteerSummary:
    def test_volunteer_summary_proper_request(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        result = client.get(
            reverse("volunteer-summary", host="api") + "?username=janeeyre",
            HTTP_HOST="api",
            **headers,
        )
        assert result.json().get("data").get("username") == "janeeyre"

    def test_volunteer_summary_wrong_key(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        headers["Authorization"] = "obviously broken key"
        result = client.get(
            reverse("volunteer-summary", host="api") + "?username=janeeyre",
            HTTP_HOST="api",
            **headers,
        )
        assert result.json() == {
            "detail": "Sorry, this resource can only be accessed by an admin API key."
        }

    def test_volunteer_summary_not_staff(self, client):
        volunteer, headers = create_volunteer(with_api_key=True)
        client.force_login(volunteer)
        result = client.get(
            reverse("volunteer-summary", host="api") + "?username=janeeyre",
            HTTP_HOST="api",
            **headers,
        )

        assert result.json() == {
            "detail": "Sorry, this resource can only be accessed by an admin API key."
        }

    def test_volunteer_summary_no_username(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        result = client.get(
            reverse("volunteer-summary", host="api"), HTTP_HOST="api", **headers
        )
        assert result.json() == {
            "error": "No username received. Use ?username= in your request."
        }

    def test_volunteer_summary_nonexistent_username(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        result = client.get(
            reverse("volunteer-summary", host="api") + "?username=asdfasdfasdf",
            HTTP_HOST="api",
            **headers,
        )
        assert result.json() == {"error": "No volunteer found with that username."}

    def test_volunteer_summary_no_key(self, client):
        result = client.get(
            reverse("volunteer-summary", host="api") + "?username=asdfasdfasdf",
            HTTP_HOST="api",
        )
        assert result.status_code == 403


class TestVolunteerAssortedFunctions:
    def test_edit_volunteer(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        data = {"username": "naaaarf"}
        assert BlossomUser.objects.get(id=1).username == "janeeyre"
        client.put(
            reverse("volunteer-detail", args=[1], host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert BlossomUser.objects.get(id=1).username == "naaaarf"

    def test_volunteer_viewset_with_qsp(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        result = client.get(
            reverse("volunteer-list", host="api") + "?username=janeeyre",
            HTTP_HOST="api",
            **headers,
        )
        r = result.json().get("results")
        assert r[0]["username"] == "janeeyre"


class TestVolunteerGammaPlusOne:
    def test_plusone(self, client):
        client, headers = create_staff_volunteer_with_keys(client)

        assert Transcription.objects.count() == 0
        assert Submission.objects.count() == 0

        jane = BlossomUser.objects.get(id=1)
        assert jane.gamma == 0

        result = client.post(
            reverse("volunteer-gamma-plusone", args=[1], host="api"),
            HTTP_HOST="api",
            **headers,
        )

        assert result.status_code == 200
        assert jane.gamma == 1
        assert Transcription.objects.count() == 1
        assert Submission.objects.count() == 1
        assert (
            Transcription.objects.get(id=1).author
            == Submission.objects.get(id=1).completed_by
            == jane
        )

    def test_plusone_with_bad_id(self, client):
        client, headers = create_staff_volunteer_with_keys(client)

        assert Transcription.objects.count() == 0
        assert Submission.objects.count() == 0

        result = client.post(
            reverse("volunteer-gamma-plusone", args=[99], host="api"),
            HTTP_HOST="api",
            **headers,
        )

        assert result.status_code == 404
        assert result.json() == {"error": "No volunteer with that ID."}
        # shouldn't have created anything
        assert Transcription.objects.count() == 0
        assert Submission.objects.count() == 0


class TestVolunteerCreation:
    def test_volunteer_create(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        data = {"username": "SPAAAACE"}
        assert BlossomUser.objects.filter(username="SPAAAACE").count() == 0
        result = client.post(
            reverse("volunteer-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 200
        assert result.json() == {
            "success": "Volunteer created with username `SPAAAACE`"
        }
        assert BlossomUser.objects.filter(username="SPAAAACE").count() == 1

    def test_volunteer_create_duplicate_username(self, client):
        client, headers = create_staff_volunteer_with_keys(client)
        data = {"username": "janeeyre"}
        assert BlossomUser.objects.filter(username="janeeyre").count() == 1
        result = client.post(
            reverse("volunteer-list", host="api"),
            json.dumps(data),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 422
        assert result.json() == {
            "error": "There is already a user with the username of `janeeyre`."
        }
        assert BlossomUser.objects.filter(username="janeeyre").count() == 1

    def test_volunteer_create_no_username(self, client):
        client, headers = create_staff_volunteer_with_keys(client)

        assert BlossomUser.objects.count() == 1
        result = client.post(
            reverse("volunteer-list", host="api"),
            HTTP_HOST="api",
            content_type="application/json",
            **headers,
        )
        assert result.status_code == 400
        assert result.json() == {"error": "Must have the `username` key in JSON body."}
        assert BlossomUser.objects.count() == 1
