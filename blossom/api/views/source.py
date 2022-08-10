"""The views of the API, providing the possible API requests."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from blossom.api.authentication import BlossomApiPermission
from blossom.api.models import Source
from blossom.api.serializers import SourceSerializer


class SourceViewSet(viewsets.ModelViewSet):
    """
    The API view to view and edit information regarding Sources.

    This information is required for both Submissions and Transcriptions.
    """

    queryset = Source.objects.all().order_by("pk")
    serializer_class = SourceSerializer
    permission_classes = (BlossomApiPermission,)
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["name"]
