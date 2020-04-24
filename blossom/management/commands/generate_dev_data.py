"""
When doing development on Blossom, it is useful to have data to work on, even if it's
not real. This bootstrap command creates a bunch of fake data just for you!

Usage: python manage.py generate_dev_data
"""

import logging
import random
import sys
import uuid
from datetime import datetime, timedelta
from time import sleep
from typing import List

import pytz
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandParser
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import CursorWrapper
from django.db.models import Max
from mimesis import Person, Text, locales

from api.models import Transcription, Submission
from blossom.management.commands import bootstrap_site

if settings.DEBUG:
    # adapted from https://stackoverflow.com/a/7769117
    # if we don't do this, you _will_ run out of memory
    BaseDatabaseWrapper.make_debug_cursor = lambda self, cursor: CursorWrapper(cursor, self)

logger = logging.getLogger("blossom.management.generate_dev_data")
transcription_template = (
    "*Image Transcription:*\n\n---\n\n{0}\n\n---\n\n^^I'm&#32;a&#32;human&#32;"
    "volunteer&#32;content&#32;transcriber&#32;for&#32;Reddit&#32;and&#32;you&"
    "#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;like&#32;more&#32;informa"
    "tion&#32;on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;we&#32;do&#32;it,&"
    "#32;click&#32;here!](https://www.reddit.com/r/TranscribersOfReddit/wiki/i"
    "ndex)"
)
transcribot_template = (
    "{0}\n\n---\n\nv0.6.0 | This message was posted by a bot. | [FAQ](https://"
    "www.reddit.com/r/TranscribersOfReddit/wiki/index) | [Source](https://gith"
    "ub.com/GrafeasGroup/tor) | Questions? [Message the mods!](https://www.red"
    "dit.com/message/compose?to=%2Fr%2FTranscribersOfReddit&subject=Bot%20Ques"
    "tion&message=)"
)


def generate_text() -> str:
    # the mimesis text package is actually only a handful of sentences for the
    # default English, and there's no reason to add more dependencies. This just
    # mashes up some of the data that's included in mimesis to make something a
    # little more random than 10 sentences' worth.
    obj = Text(random.choice(locales.LIST_OF_LOCALES))
    if random.random() > 0.49:
        return obj.text()
    else:
        return ' '.join(obj.words(random.randrange(16, 40)))


def get_image_urls(num: int) -> List[str]:
    """
    Retrieve the requested number of URLs from https://dog.ceo's API. This is
    used so that submission objects have actual URLs with content attached to
    them in case you're working on something that needs that information.
    """
    number_of_calls, remainder = divmod(num, 50)
    results = list()

    for _ in range(number_of_calls):
        # the maximum the api will accept in a single call is 50, so we batch them
        results = results + requests.get(
            "https://dog.ceo/api/breeds/image/random/50"
        ).json()["message"]
        # be nice
        sleep(0.5)

    if remainder > 0:
        results = results + requests.get(
            f"https://dog.ceo/api/breeds/image/random/{remainder}"
        ).json()["message"]

    return results


def gen_datetime(min_year: int=2017, max_year: datetime=datetime.now().year) -> datetime:
    # Adapted from https://gist.github.com/rg3915/db907d7455a4949dbe69
    start = datetime(min_year, 1, 1, 00, 00, 00)
    years = max_year - min_year + 1
    end = start + timedelta(days=365 * years)
    return (start + (end - start) * random.random()).replace(tzinfo=pytz.UTC)


def create_dummy_volunteers(num: int) -> None:
    users = get_user_model()
    for _ in range(num):
        username = Person().username()
        if not users.objects.filter(username=username).exists():
            volunteer = users.objects.create(username=username, accepted_coc=True)
            # there shouldn't be a need to log in as a volunteer, but if we
            # need to test something, then let's set every dummy account
            # password to the same value.
            volunteer.set_password('asdf')
            volunteer.save()


def create_dummy_submissions(no_urls: bool) -> None:
    users = get_user_model()
    transcribot = users.objects.get(username="transcribot")
    # adapted from
    # https://books.agiliq.com/projects/django-orm-cookbook/en/latest/random.html
    max_id = users.objects.all().aggregate(max_id=Max("id"))['max_id']
    if no_urls == True:
        logger.warning("SKIPPING IMAGES")
        urls = [None]
    else:
        logger.warning("GETTING IMAGES")
        urls = get_image_urls(int(users.objects.count() / 2))

    # quintuple the submission objects than volunteers so we've got plenty to
    # play with
    for _ in range(users.objects.count() * 5):
        while True:
            pk = random.randint(1, max_id)
            volunteer = users.objects.filter(pk=pk).first()
            if volunteer:
                break

        submission_date = gen_datetime()
        submission = Submission.objects.create(
            submission_id=uuid.uuid4(),
            submission_time=submission_date,
            claimed_by=volunteer,
            completed_by=volunteer,
            claim_time=submission_date + timedelta(hours=2),
            complete_time=submission_date + timedelta(
                hours=2, minutes=random.choice(range(40))
            ),
            source="bootstrap script",
            url=random.choice(urls),
            archived=random.choice([True, False])
        )
        Transcription.objects.create(
            submission=submission,
            author=transcribot,
            post_time=submission.complete_time - timedelta(minutes=1),
            transcription_id=uuid.uuid4(),
            completion_method='bootstrap script',
            url=None,
            ocr_text=transcribot_template.format(generate_text())
        )


def create_dummy_transcriptions() -> None:
    users = get_user_model()
    # adapted from
    # https://books.agiliq.com/projects/django-orm-cookbook/en/latest/random.html
    max_id = Submission.objects.all().aggregate(max_id=Max("id"))['max_id']
    # every volunteer has transcriptions, it's just a question of how many
    for _ in users.objects.all():
        for __ in range(1, 5):
            while True:
                pk = random.randint(1, max_id)
                submission = Submission.objects.filter(pk=pk).first()
                if submission:
                    break

            Transcription.objects.create(
                submission=submission,
                author=submission.claimed_by,
                post_time=submission.submission_time + timedelta(minutes=1),
                transcription_id=uuid.uuid4(),
                completion_method='bootstrap script',
                url=None,
                text=transcription_template.format(generate_text())
            )


class Command(BaseCommand):
    help = "Creates dummy data for development purposes."
    include_urls = True

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--no_urls',
            action='store_true',
            help='Do not fetch URLs for submission objects.',
        )

    def handle(self, *args, **options) -> None:
        # make it so that a person only has to run one bootstrap command if they want to
        bootstrap_site.Command().handle()

        if Transcription.objects.count() > 0 \
                or Submission.objects.count() > 0 \
                or get_user_model().objects.count() > 5:
            answer = input(self.style.WARNING(
                "WAIT! There is already data in the db. Are you sure you want to run"
                " this? [y/N] ")
            )
            if not answer.lower().startswith('y'):
                logger.info(self.style.ERROR('Exiting!'))
                sys.exit(0)

        logger.info(
            self.style.WARNING("This process will take a few minutes. Please be patient.")
        )
        logger.info(self.style.NOTICE("Creating volunteers..."))
        create_dummy_volunteers(1000)
        logger.info(self.style.SUCCESS("OK!\n"))

        logger.info(self.style.NOTICE("Creating submissions..."))
        create_dummy_submissions(no_urls=options['no_urls'])
        logger.info(self.style.SUCCESS("OK!\n"))

        logger.info(self.style.NOTICE("Creating transcriptions..."))
        create_dummy_transcriptions()
        logger.info(self.style.SUCCESS("OK!\n"))

        logger.info(self.style.NOTICE("All done!"))
