"""The API to handle creation and updating of users and transcriptions."""
from typing import Dict

import pytz
from blossom.api.models import Transcription
from blossom.authentication.models import BlossomUser
from django.utils import timezone


class Summary:
    """A summary view of the current state of the system."""

    @staticmethod
    def generate_summary() -> Dict:
        """
        Generate a summary from the current state of the system.

        The following is returned:
        - "volunteer_count":        the total number of volunteers
        - "transcription_count":    the total number of transcriptions
        - "days_since_inception":   number of days since the subreddit was founded

        :return: dictionary with the items described above
        """
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
