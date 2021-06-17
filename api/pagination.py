from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """The standard pagination class to use for the queries."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 500
