import json

from django_hosts.resolvers import reverse

from blossom.slack_conn.helpers import process_message


# TODO: There is a way to mock decorators, but I can't figure it out.
# There's a lot of testing that needs to happen for this module, but I can't
# get past the threading decorator and the patch calls don't seem to work.
# Resources:
# https://stackoverflow.com/questions/7667567/can-i-patch-a-python-decorator-before-it-wraps-a-function
# http://alexmarandon.com/articles/python_mock_gotchas/
# https://stackoverflow.com/questions/36812830/mocking-decorators-in-python-with-mock-and-pytest


def test_challenge_request(client):
    # If there is a challenge value in the request, immediately return it
    data = {"challenge": "asdfasdfasdf"}
    result = client.post(
        reverse("slack", host="www"),
        json.dumps(data),
        HTTP_HOST="www",
        content_type="application/json",
    )
    assert result.content == b'asdfasdfasdf'
