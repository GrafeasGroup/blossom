from django.conf.urls import include
from django.conf.urls import url
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework import routers

from blossom.api import views

schema_view = get_schema_view(
    openapi.Info(
      title="Grafeas Group - Transcriptions API",
      default_version='v1',
      description="Handy-dandy API reference for our work on Reddit and elsewhere!",
      terms_of_service="https://grafeas.org/posts/3-terms-of-service/",
      contact=openapi.Contact(email="devs@grafeas.org"),
      license=openapi.License(name="All Rights Reserved"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    urlconf="blossom.api.urls"
)

# automatically build URLs, as recommended by django-rest-framework docs
router = routers.DefaultRouter()
router.register(r"volunteer", views.VolunteerViewSet, basename="volunteer")
router.register(r"submission", views.SubmissionViewSet, basename="submission")
router.register(r"transcription", views.TranscriptionViewSet, basename="transcription")

urlpatterns = [
    url(r"", include(router.urls)),
    url(r"^auth/", include("rest_framework.urls")),
    url(r"^summary/", views.SummaryView.as_view()),
    url(
        r'^swagger(?P<format>\.json|\.yaml)$',
        schema_view.without_ui(cache_timeout=0),
        name='schema-json'
    ),
    url(
        r'^swagger/$',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui'
    ),
    url(
        r'^redoc/$',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc'
    ),
]
