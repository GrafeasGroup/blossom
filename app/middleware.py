import logging

from django.conf import settings
from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject
from praw import Reddit
from social_django.utils import load_strategy

log = logging.getLogger(__name__)


def refresh_token(request: HttpRequest) -> None:
    """Refresh the OAuth token so that we can use it."""
    strategy = load_strategy(request)
    social = request.user.social_auth.filter(provider="reddit")[0]
    social.refresh_token(
        strategy=strategy, redirect_uri="http://localhost:8000/complete/reddit/"
    )


def configure_reddit(request: HttpRequest) -> Reddit:
    """Build the reddit instance that will be attached to the user."""
    reddit = Reddit(
        client_id=settings.SOCIAL_AUTH_REDDIT_KEY,
        client_secret=settings.SOCIAL_AUTH_REDDIT_SECRET,
        refresh_token=request.user.social_auth.first().extra_data["refresh_token"],
        user_agent=(
            f"blossomtest, logged in as {request.user.username};"
            f" contact u/itsthejoker with questions."
        ),
    )

    return reddit


class RedditMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest) -> None:
        """Add the built Reddit object to the request if it's available."""
        if not request.user.is_authenticated:
            # Don't trigger on anonymous users
            return
        if not request.user.social_auth.first():
            # Don't do anything if we don't have social auth hooked up
            return
        if not hasattr(request.user.social_auth.first(), "extra_data"):
            # Safety check; make sure the extra data dict exists
            return
        if not request.user.social_auth.first().extra_data.get("refresh_token"):
            # We won't have a refresh token if we just started the process
            refresh_token(request)
        # Build a pre-authenticated reddit instance and attach it to the request.
        # This will be finished when it's called.
        request.user.reddit = SimpleLazyObject(lambda: configure_reddit(request))
