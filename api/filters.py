import dateparser
from django.db.models.query import QuerySet
from django.db.models.query_utils import Q
from rest_framework.filters import BaseFilterBackend
from rest_framework.request import Request
from rest_framework.views import View


class TimeFilter(BaseFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: QuerySet, view: View
    ) -> QuerySet:
        """Attempt to filter a request by time descriptors if available."""
        dateparser_settings = {
            "TIMEZONE": "+0000",
            "RETURN_AS_TIMEZONE_AWARE": True,
        }
        filters = Q()
        if from_time := request.query_params.get("from"):
            from_datetime = dateparser.parse(from_time, settings=dateparser_settings)
            if from_datetime is not None:
                filters = filters & Q(complete_time__gt=from_datetime)

        if until_time := request.query_params.get("until"):
            until_datetime = dateparser.parse(until_time, settings=dateparser_settings)
            if until_datetime is not None:
                filters = filters & Q(complete_time__lt=until_datetime)

        return queryset.filter(filters)


class CaseInsensitiveUsernameFilter(BaseFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: QuerySet, view: View
    ) -> QuerySet:
        """Filter by username using the __iexact query method."""
        if username := request.query_params.get("username"):
            queryset = queryset.filter(username__iexact=username)
        return queryset
