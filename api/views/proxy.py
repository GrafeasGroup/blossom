import random
import string

import requests
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from revproxy.views import ProxyView


def generate_request_id() -> str:
    """Create a random 6-digit string to make Reddit's user-agent guard happy."""
    return "".join([random.choice(string.ascii_lowercase) for _ in range(6)])


class iReddItProxyView(ProxyView):  # noqa: N801
    """
    Retrieve images for OpenSeaDragon from Reddit's image host.

    Reddit does not set the appropriate CORS headers on their image host so that
    images can be pulled using AJAX (which is what OpenSeaDragon uses). The only ways
    to get around this are:

    a) ask Reddit politely to add the correct headers
    b) don't load the image at all
    c) proxy requests to i.redd.it through our own server, which doesn't have the same
       restrictions that the browser does

    Usage:

    GET .../api/iredditproxy/abcde.jpg
    The above request will load https://i.redd.it/abcde.jpg, then serve it from our
    server so that OpenSeaDragon can load it. Normally it would probably be reasonable
    to implement this in nginx instead of Django, but 1) I don't see this being that
    much of an issue and 2) doing it this way means that we can use it on local dev as
    well.
    """

    upstream = "https://i.redd.it/"


class ImgurProxyView(ProxyView):
    """Proxy for retrieving images from Imgur."""

    upstream = "https://imgur.com"


@csrf_exempt
def subreddit_json_proxy_view(request: HttpRequest) -> JsonResponse:
    """Proxy for retrieving information from Reddit about subreddits."""
    if sub_name := request.GET.get("s"):
        if not sub_name.startswith("/r/"):
            # it's a source, but it's not a source from Reddit. We'll handle these
            # eventually, but for now just return an empty response.
            return JsonResponse({})

        request_id = generate_request_id()
        headers = {
            "User-Agent": f"Python:Blossom:ID:{request_id} - contact u/itsthejoker"
        }
        response = requests.get(
            f"https://www.reddit.com{sub_name}/about/rules.json", headers=headers
        )
        response.raise_for_status()
        return JsonResponse(response.json())
    # the request came in malformed -- just say everything's fine.
    return JsonResponse({})
