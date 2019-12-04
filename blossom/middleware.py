import sys
from better_exceptions import excepthook

# For debug purposes only. Link to local_settings by adding `blossom.middleware.BetterExceptionsMiddleware`
# to the top of the middleware stack.
class BetterExceptionsMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        excepthook(exception.__class__, exception, sys.exc_info()[2])
        return None
