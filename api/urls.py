"""URL configuration for the API application."""
from django.conf.urls import include, url
from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers

from api import (
    misc_views,
    source_views,
    submission_views,
    transcription_views,
    volunteer_views,
)
from api.slack_conn import views as slack_views

schema_view = get_schema_view(
    openapi.Info(
        title="Grafeas Group - Transcriptions API",
        default_version="v1",
        description="Handy-dandy API reference for our work on Reddit and elsewhere!",
        terms_of_service="https://grafeas.org/posts/3-terms-of-service/",
        contact=openapi.Contact(email="devs@grafeas.org"),
        license=openapi.License(name="MIT"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    urlconf="api.urls",
)

# automatically build URLs, as recommended by django-rest-framework docs
router = routers.DefaultRouter()
router.register(r"volunteer", volunteer_views.VolunteerViewSet, basename="volunteer")
router.register(
    r"submission", submission_views.SubmissionViewSet, basename="submission"
)
router.register(
    r"transcription", transcription_views.TranscriptionViewSet, basename="transcription"
)
router.register(r"source", source_views.SourceViewSet, basename="source")

urlpatterns = [
    url(r"", include(router.urls)),
    url(r"^auth/", include("rest_framework.urls")),
    url(r"^summary/", misc_views.SummaryView.as_view(), name="summary"),
    url(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    url(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    url(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
    url(r"^ping/", misc_views.PingView.as_view(), name="ping"),
    path("slack/endpoint/", slack_views.slack_endpoint, name="slack"),
    path(
        "slack/github/sponsors/", slack_views.github_sponsors_endpoint, name="github_sponsors"
    ),
]
