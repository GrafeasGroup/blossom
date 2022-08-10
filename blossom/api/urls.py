"""URL configuration for the API application."""
from typing import Any, Dict, Tuple

from django.conf.urls import include, url
from django.urls import path
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers

from blossom.api.views import (
    find,
    misc,
    plausible,
    proxy,
    slack,
    source,
    submission,
    transcription,
    volunteer,
)


class CustomOpenAPISchemaGenerator(OpenAPISchemaGenerator):
    """
    Custom schema generator required for Swagger to point the requests to correct URL.

    See https://github.com/axnsan12/drf-yasg/issues/146#issuecomment-478757552.
    """

    def get_schema(
        self, *args: Tuple[Any, ...], **kwargs: Dict[str, Any]
    ) -> openapi.Swagger:
        """Generate a :class:`.Swagger` object representing the API schema.

        :param request: the request used for filtering accessible endpoints and finding
        the spec URI
        :type request: rest_framework.request.Request or None
        :param bool public: if True, all endpoints are included regardless of access
        through `request`
        :param args: the args for the schema
        :param kwargs: the kwargs for the schema

        :return: the generated Swagger specification
        :rtype: openapi.Swagger
        """
        schema = super().get_schema(*args, **kwargs)
        # This makes sure that Swagger points to the /api/ endpoint.
        schema.basePath = "/api"
        return schema


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
    urlconf="blossom.api.urls",
    generator_class=CustomOpenAPISchemaGenerator,
)

# automatically build URLs, as recommended by django-rest-framework docs
router = routers.DefaultRouter()
router.register(r"volunteer", volunteer.VolunteerViewSet, basename="volunteer")
router.register(r"submission", submission.SubmissionViewSet, basename="submission")
router.register(
    r"transcription", transcription.TranscriptionViewSet, basename="transcription"
)
router.register(r"source", source.SourceViewSet, basename="source")

urlpatterns = [
    url(r"", include(router.urls)),
    url(r"^summary/", misc.SummaryView.as_view(), name="summary"),
    url(r"^find/", find.FindView.as_view(), name="find"),
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
    url(r"^ping/", misc.PingView.as_view(), name="ping"),
    path("slack/endpoint/", slack.slack_endpoint, name="slack"),
    path(
        "slack/github/sponsors/",
        slack.github_sponsors_endpoint,
        name="github_sponsors",
    ),
    url(
        r"^iredditproxy/(?P<path>.*)$",
        proxy.iReddItProxyView.as_view(),
        name="iredditproxy",
    ),
    url(
        r"^imgurproxy/(?P<path>.*)$", proxy.ImgurProxyView.as_view(), name="imgurproxy"
    ),
    path(
        "subredditjsonproxy/",
        proxy.subreddit_json_proxy_view,
        name="subredditjsonproxy",
    ),
    path("event", plausible.plausible_event),
]
