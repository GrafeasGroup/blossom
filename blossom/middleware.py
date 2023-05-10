import sys
from typing import Callable

from better_exceptions import excepthook
from django.http import HttpRequest, HttpResponse


class BetterExceptionsMiddleware(object):
    def __init__(self, get_response: Callable) -> None:
        """For debug purposes only.

        Link to local_settings by adding
        `blossom.middleware.BetterExceptionsMiddleware`
        to the top of the middleware stack.
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Override call functionality."""
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        """Allow BetterExceptions to hook into the running process."""
        excepthook(exception.__class__, exception, sys.exc_info()[2])
        return None
