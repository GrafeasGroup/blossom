import logging
from typing import Any

import prawcore
from django.core.management.base import BaseCommand

from api.models import Submission
from blossom.reddit import REDDIT

logger = logging.getLogger("blossom.management.validate_images")

IMAGE_DOMAINS = [
    "imgur.com",
    "i.imgur.com",
    "m.imgur.com",
    "i.reddit.com",
    "i.redd.it",
    "puu.sh",
    "i.redditmedia.com",
]


class Command(BaseCommand):
    help = "Check all submissions in the db to check if they're images."  # noqa: VNE003

    def handle(self, *args: Any, **options: Any) -> None:
        """See help message."""
        subs = Submission.objects.filter(is_image=True, image_url=None)
        logger.info(
            self.style.SUCCESS(
                f"Total to process: {len(subs)} out of {Submission.objects.count()}"
                f" - {(1 - (len(subs) / Submission.objects.count())) * 100:.2f}% done"
            )
        )

        if len(subs) == 0:
            logger.info(self.style.SUCCESS("Nothing to do!"))
            return

        for sub in subs:
            logger.info(self.style.SUCCESS(f"Processing {sub.original_id}"))
            try:
                image_url = REDDIT.submission(url=sub.url).url
                sub.image_url = image_url
                sub.save()
            except (prawcore.exceptions.Forbidden, prawcore.exceptions.NotFound):
                sub.is_image = False
                sub.save()
