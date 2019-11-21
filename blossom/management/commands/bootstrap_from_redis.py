from django.core.management.base import BaseCommand

from blossom.api.bootstrap.main import BOOTSTRAP_THAT_MOFO


class Command(BaseCommand):
    help = 'Pulls entries from Redis and shoves them in the database. Again.'

    def handle(self, *args, **options):
        BOOTSTRAP_THAT_MOFO()
