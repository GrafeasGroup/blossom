from django.db.models.query import QuerySet
from rest_framework.filters import BaseFilterBackend
from rest_framework.request import Request
from rest_framework.views import View


class CaseInsensitiveUsernameFilter(BaseFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: QuerySet, view: View
    ) -> QuerySet:
        """Filter by username using the __iexact query method."""
        if username := request.query_params.get("username"):
            queryset = queryset.filter(username__iexact=username)
        return queryset
