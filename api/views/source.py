"""The views of the API, providing the possible API requests."""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter

from api.authentication import BlossomApiPermission
from api.models import Source
from api.serializers import SourceSerializer


class SourceViewSet(viewsets.ModelViewSet):
    """
    The API view to view and edit information regarding Sources.

    This information is required for both Submissions and Transcriptions.
    """

    queryset = Source.objects.all().order_by("pk")
    serializer_class = SourceSerializer
    permission_classes = (BlossomApiPermission,)
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        "name": ["exact", "icontains", "istartswith"],
        "origin": ["exact"],
        "disabled": ["exact", "isnull"],
        "moderator": ["exact", "isnull"],
        "reddit_upvote_filter": ["exact", "gt", "gte", "lte", "lt"],
    }
    ordering_fields = [
        "name",
        "origin",
        "reddit_upvote_filter",
    ]
