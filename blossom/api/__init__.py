import pytz
from django.utils import timezone

from blossom.api.models import Transcription
from blossom.authentication.models import BlossomUser


class Summary(object):
    """
    A basic object that just generates a summary view that's easy to access.
    """

    def generate_summary(self):
        # subtract 2 from volunteer count for anon volunteer and u/ToR
        return {
            "volunteer_count": BlossomUser.objects.filter(is_volunteer=True).count()
            - 2,
            "transcription_count": Transcription.objects.count(),
            "days_since_inception": (
                timezone.now()
                - pytz.timezone("UTC").localize(
                    timezone.datetime(day=1, month=4, year=2017), is_dst=None
                )
            ).days,
        }
