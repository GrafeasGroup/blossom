from django.urls import path

from blossom.slack_conn import views

urlpatterns = [
    path("slack/endpoint/", views.slack_endpoint, name="slack"),
    path(
        "slack/github/sponsors/", views.github_sponsors_endpoint, name="github_sponsors"
    ),
]
