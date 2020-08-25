import os
from unittest.mock import MagicMock

from django.conf import settings
from praw import Reddit

# This is abstracted out for testing purposes so that it's easy to override.

if settings.ENABLE_OCR:
    REDDIT = Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_SECRET"),
        password=os.getenv("REDDIT_PASSWORD"),
        username=os.getenv("REDDIT_USERNAME"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
    )
else:
    REDDIT = MagicMock()
