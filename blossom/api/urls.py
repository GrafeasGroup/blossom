from django.conf.urls import url
from django.conf.urls import include
from rest_framework import routers
from blossom.api import views

from rest_framework_swagger.views import get_swagger_view

schema_view = get_swagger_view(title="Blossom API")

# automatically build URLs, as recommended by django-rest-framework docs
router = routers.DefaultRouter()
router.register(r"volunteer", views.VolunteerViewSet, basename="volunteer")
router.register(r"post", views.PostViewSet, basename="post")
router.register(r"transcription", views.TranscriptionViewSet, basename="transcription")

urlpatterns = [
    url(r"", include(router.urls)),
    url(r"^auth/", include("rest_framework.urls")),
    url(r"^swagger/", schema_view),
    url(r"^summary/", views.SummaryView.as_view()),
]
