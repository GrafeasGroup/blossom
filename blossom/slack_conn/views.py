import json

from django.http import HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt

from blossom.slack_conn.helpers import process_message


@csrf_exempt
def slack_endpoint(request: HttpRequest) -> HttpResponse:
    """
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

    :param request: HttpRequest
    :return: JsonResponse, HttpRequest
    """
    json_data = json.loads(request.body)
    if json_data.get('challenge'):
        # looks like we got hit with the magic handshake packet. Send it
        # back to its maker.
        return HttpResponse(json_data['challenge'])
    # It's not a challenge, so just hand off data processing to the
    # thread and give Slack the result it craves.
    process_message(json_data)
    return HttpResponse(status=200)
