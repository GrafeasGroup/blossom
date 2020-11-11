"""Views that specifically relate to communication with Slack."""
import json

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from api.views.slack_helpers import (
    is_valid_github_request,
    process_message,
    send_github_sponsors_message,
)


@csrf_exempt
def slack_endpoint(request: HttpRequest) -> HttpResponse:
    """
    Handle post requests from Slack.

    Slack plays a lot of games with its API and honestly it's one of the
    most frustrating things I've ever worked with. There are a couple of
    things that we'll need to do in this view:

    * No matter what, respond within three seconds _of slack sending the
      ping_ -- we really have less than three seconds. Slack is impatient.
      Slack cares not for your feelings.
    * Sometimes we'll get a challenge that we have to respond to, but it's
      unclear if we'll only get it during setup or whenever Slack feels
      like it.

    So how do we get around Slack's ridiculous timeouts?

    ⋆ . ˚ * ✧ T H R E A D I N G ✧ * ˚ . ⋆
    -------------------------------------

    We extract the information we need out of the request, pass it off
    to a different function to actually figure out what the hell Slack
    wants, and then send our own response. In the meantime, we basically
    just send a 200 OK as fast as we can so that Slack doesn't screw up
    our day.

    Modifying the request URL on Slack's side is done under the Event
    Subscriptions tab under "Your Apps".

    :param request: HttpRequest
    :return: HttpRequest
    """
    json_data = json.loads(request.body)
    if json_data.get("challenge"):
        # looks like we got hit with the magic handshake packet. Send it
        # back to its maker.
        return HttpResponse(json_data["challenge"])
    # It's not a challenge, so just hand off data processing to the
    # thread and give Slack the result it craves.
    process_message(json_data)
    return HttpResponse(status=200)


@csrf_exempt
def github_sponsors_endpoint(request: HttpRequest) -> HttpResponse:
    """
    Translate GitHub Sponsors webhook to Slack webhook.

    GitHub does not provide the ability to change the format of their webhooks,
    so we have to provide a translation layer. This function is an adaptation
    of alexellis' work linked below.

    resources:
    - https://developer.github.com/webhooks/event-payloads/#sponsorship
    - https://github.com/alexellis/sponsors-functions/blob/master/
        sponsors-receiver/handler.js
    """
    if not is_valid_github_request(request):
        # Don't know what it was, but it wasn't legit. Just say everything's groovy.
        return HttpResponse(status=200)

    data = json.loads(request.body.decode())

    if action := data.get("action"):
        send_github_sponsors_message(data, action)
    return HttpResponse(status=200)
