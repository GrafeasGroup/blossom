from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from website.helpers import get_additional_context
from website.models import Post


def index(request: HttpRequest) -> HttpResponse:
    """Render the homepage for the engineering posts."""
    posts = Post.objects.filter(
        published=True,
        engineeringblogpost=True,
        standalone_section=False,
        show_in_news_view=True,
    ).order_by("-date")

    context = get_additional_context({"posts": posts})

    return render(request, "website/index.html", context)
