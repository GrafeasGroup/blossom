import dateparser
from django.db.models.query import QuerySet
from django.db.models.query_utils import Q
from django.utils import timezone
from rest_framework.filters import BaseFilterBackend
from rest_framework.request import Request
from rest_framework.views import View


class TimeFilter(BaseFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: QuerySet, view: View
    ) -> QuerySet:
        """Attempt to filter a request by time descriptors if available."""
        filters = Q()
        if from_time := request.query_params.get("from"):
            try:
                filters = filters & Q(
                    complete_time__gt=timezone.make_aware(dateparser.parse(from_time))
                )
            except AttributeError:
                pass

        if until_time := request.query_params.get("until"):
            try:
                filters = filters & Q(
                    complete_time__lt=timezone.make_aware(dateparser.parse(until_time))
                )
            except AttributeError:
                pass

        return queryset.filter(filters)


class CaseInsensitiveUsernameFilter(BaseFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: QuerySet, view: View
    ) -> QuerySet:
        """Filter by username using the __iexact query method."""
        if username := request.query_params.get("username"):
            queryset = queryset.filter(username__iexact=username)
        return queryset
