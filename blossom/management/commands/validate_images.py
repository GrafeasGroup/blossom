import logging
from urllib.parse import urlparse

import prawcore
from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Submission

logger = logging.getLogger("blossom.management.validate_images")


class Command(BaseCommand):
    help = "Go through all submissions in the db to validate if it's an image or not."

    def handle(self, *args, **options):
        image_domains = [
            "imgur.com",
            "i.imgur.com",
            "m.imgur.com",
            "i.reddit.com",
            "i.redd.it",
            "puu.sh",
            "i.redditmedia.com",
        ]
        subs = Submission.objects.filter(is_image=None)
        logger.info(
            self.style.SUCCESS(
                f"Total to process: {len(subs)} out of {Submission.objects.count()}"
                f" - {(1-(len(subs)/Submission.objects.count()))*100:.2f}% done"
            )
        )

        if len(subs) == 0:
            logger.info(self.style.SUCCESS("Nothing to do!"))
            return

        for sub in subs:
            logger.info(self.style.SUCCESS(f"Processing {sub.original_id}"))
            if not sub.url:
                sub.is_image = False
                sub.save()
                continue
            try:
                if (
                    urlparse(settings.REDDIT.submission(url=sub.url).url).netloc
                    in image_domains
                ):
                    sub.is_image = True
                    sub.save()
                else:
                    sub.is_image = False
                    sub.save()
            except (prawcore.exceptions.Forbidden, prawcore.exceptions.NotFound):
                sub.is_image = False
                sub.save()
