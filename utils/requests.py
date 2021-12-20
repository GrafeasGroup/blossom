from django.http import HttpRequest
from rest_framework.request import Request


def convert_to_drf_request(request: HttpRequest, data: dict = None) -> Request:
    """
    Convert a standard Django request to the DRF equivalent.

    DRF ViewSets can't take normal Django requests, so any interaction with the
    API side must involve converting the request object before sending it off.
    We also occasionally want to have data on it to make the API happy, so this
    function also handles that.
    """
    new_request = Request(request)
    new_request._full_data = data
    return new_request
