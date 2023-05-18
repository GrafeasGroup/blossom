from django.urls import path

from slack_bolt.adapter.django import SlackRequestHandler
from blossom.slackapp.listeners import app

# this enables all commands
import blossom.slackapp.commands  # noqa

handler = SlackRequestHandler(app=app)

from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def slack_events_handler(request: HttpRequest):
    return handler.handle(request)


urlpatterns = [
    path("api/slack/endpoint", slack_events_handler, name="slack_events"),
]
