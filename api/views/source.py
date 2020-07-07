"""The views of the API, providing the possible API requests."""

from rest_framework import viewsets

from api.authentication import AdminApiKeyCustomCheck
from api.models import Source
from api.serializers import SourceSerializer


class SourceViewSet(viewsets.ModelViewSet):
    """
    The API view to view and edit information regarding Sources.

    This information is required for both Submissions and Transcriptions.
    """

    queryset = Source.objects.all().order_by("pk")
    serializer_class = SourceSerializer
    permission_classes = (AdminApiKeyCustomCheck,)