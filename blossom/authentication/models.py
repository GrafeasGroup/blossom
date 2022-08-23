"""Models used within the Authentication application."""
import random
from datetime import datetime, timedelta
from typing import Any, Optional

import pytz
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework_api_key.models import APIKey

from blossom.api.models import Submission

# A list of gamma values and corresponding check percentages.
# An entry (x, y) means that if the user has <= x gamma,
# they should be checked with a probability of y.
AUTO_CHECK_PERCENTAGES = [
    (10, 1),
    (50, 0.5),
    (100, 0.3),
    (250, 0.15),
    (500, 0.05),
    (1000, 0.02),
    (5000, 0.01),
]

# The check percentage for very high gamma users.
# Used as a fallback if the list above does not contain an entry.
HIGH_GAMMA_CHECK_PERCENTAGE = 0.005

# Time period to check low activity
LOW_ACTIVITY_TIMEDELTA = timedelta(days=30)
# Transcription count where a volunteer activity is marked as low
LOW_ACTIVITY_THRESHOLD = 10


class BlossomUserManager(UserManager):
    # https://stackoverflow.com/a/7774039
    def filter(self, **kwargs: Any) -> QuerySet:  # noqa: ANN401
        """Override `filter` to make usernames case insensitive."""
        if "username" in kwargs:
            kwargs["username__iexact"] = kwargs["username"]
            del kwargs["username"]
        return super().filter(**kwargs)

    def get(self, **kwargs: Any) -> QuerySet:  # noqa: ANN401
        """Override `get` to make usernames case insensitive."""
        if "username" in kwargs:
            kwargs["username__iexact"] = kwargs["username"]
            del kwargs["username"]
        return super().get(**kwargs)


class BlossomUser(AbstractUser):
    """
    The user class used within the program.

    Note that this class provides some additional properties based on the current
    status of the user and the roles they fulfill.
    """

    class Meta:
        indexes = [models.Index(fields=["username", "email"])]

    # The backend class which is used to authenticate the BlossomUser.
    backend = "blossom.authentication.backends.EmailBackend"

    # TODO: abstract out to role / permission / group
    # A boolean that denotes whether a user account belongs to a volunteer or not.
    is_volunteer = models.BooleanField(default=True)
    # A boolean that denotes whether a user account is a staff account with Grafeas.
    # (not to be confused with the base Django staff account.)
    is_grafeas_staff = models.BooleanField(default=False)

    # A boolean that denotes whether a user is a bot account.
    is_bot = models.BooleanField(default=False)

    # Each person is allowed one API key, but advanced security around this
    # means that it is not fully implemented at this time. It is used by
    # u/transcribersofreddit and the other bots, though.
    api_key = models.OneToOneField(
        APIKey, on_delete=models.CASCADE, null=True, blank=True
    )

    # The percentage used to determine if a transcription should be checked by the mods.
    # If this is set, it will overwrite the automatically determined percentage
    # based on the user's gamma.
    # This must be a number between 0 and 1 (inclusive).
    overwrite_check_percentage = models.FloatField(null=True, blank=True, default=None)

    # The time that this record was last updated.
    last_update_time = models.DateTimeField(default=timezone.now)
    # Whether this particular user has accepted our Code of Conduct.
    accepted_coc = models.BooleanField(default=False)

    # Whether the user is blocked; if so, any transcribing activity will not be
    # processed.
    blocked = models.BooleanField(default=False)

    objects = BlossomUserManager()

    def date_last_active(self) -> Optional[datetime]:
        """Return the time where the user was last active.

        This will give the time where the user last claimed or completed a post.
        """
        recently_claimed = (
            Submission.objects.filter(claimed_by=self).order_by("-claim_time").first()
        )
        recent_claim_time = recently_claimed.claim_time if recently_claimed else None

        recently_completed = (
            Submission.objects.filter(completed_by=self)
            .order_by("-complete_time")
            .first()
        )
        recent_complete_time = (
            recently_completed.complete_time if recently_completed else None
        )

        if recent_claim_time and recent_complete_time:
            return max(recent_complete_time, recent_claim_time)

        return recent_claim_time or recent_complete_time

    @property
    def gamma(self) -> int:
        """
        Return the number of transcriptions the user has made.

        Note that this is a calculated property, computed by the number of
        transcriptions in the database.

        :return: the number of transcriptions written by the user.
        """
        return self.gamma_at_time(start_time=None, end_time=None)

    def gamma_at_time(
        self,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """Return the number of transcriptions the user has made in the given time-frame.

        :param start_time: The time to start counting transcriptions from.
        :param end_time: The time to end counting transcriptions to.
        """
        if self.blocked:
            return 0  # see https://github.com/GrafeasGroup/blossom/issues/15

        filters = {
            "completed_by": self,
        }
        if start_time:
            filters["complete_time__gte"] = start_time
        if end_time:
            filters["complete_time__lte"] = end_time

        return Submission.objects.filter(**filters).count()

    def __str__(self) -> str:
        return self.username

    # Disable complexity check, it's not really hard to understand
    def get_rank(self, override: int = None) -> str:  # noqa: C901
        """
        Return the name of the volunteer's current rank.

        Override provided for the purposes of checking ranks.
        """
        gamma = override if override else self.gamma

        if gamma >= 20000:
            return "Sapphire"
        elif gamma >= 10000:
            return "Jade"
        elif gamma >= 5000:
            return "Topaz"
        elif gamma >= 2500:
            return "Ruby"
        elif gamma >= 1000:
            return "Diamond"
        elif gamma >= 500:
            return "Gold"
        elif gamma >= 250:
            return "Purple"
        elif gamma >= 100:
            return "Teal"
        elif gamma >= 50:
            return "Green"
        elif gamma >= 25:
            return "Pink"
        else:
            return "Initiate"

    @property
    def ranked_up(self) -> bool:
        """Determine whether the user has just ranked up."""
        return self.get_rank() != self.get_rank(override=self.gamma - 1)

    @property
    def has_low_activity(self) -> bool:
        """Determine if the volunteer currently has a low activity.

        This will be true if the volunteer has only done very few transcriptions recently.
        """
        recent_date = datetime.now(tz=pytz.UTC) - LOW_ACTIVITY_TIMEDELTA
        recent_transcriptions = Submission.objects.filter(
            completed_by=self,
            complete_time__gte=recent_date,
        ).count()

        return recent_transcriptions <= LOW_ACTIVITY_THRESHOLD

    @property
    def auto_check_percentage(self) -> float:
        """Determine the probability for automatic transcription checks."""
        for (gamma, percentage) in AUTO_CHECK_PERCENTAGES:
            if self.gamma <= gamma:
                return percentage

        return HIGH_GAMMA_CHECK_PERCENTAGE

    @property
    def check_percentage(self) -> float:
        """Determine the current probability for transcription checks.

        This is either the watch percentage if the user is being watched
        or the percentage for automatic checks.
        """
        return self.overwrite_check_percentage or self.auto_check_percentage

    def should_check_transcription(self) -> bool:
        """Determine if a transcription should be checked for this user."""
        return self.has_low_activity or random.random() <= self.check_percentage

    def transcription_check_reason(self, ignore_low_activity: bool = False) -> str:
        """Determine the current reason for checking transcriptions.

        - Low transcribing activity by the volunteer (can be disabled by setting
          ignore_low_activity to True).
        - The user is being watched by the mods.
        - Automatic checks.
        """
        if self.has_low_activity and not ignore_low_activity:
            return "Low activity"

        return "{reason} ({percentage:.1%})".format(
            reason="Watched" if self.overwrite_check_percentage else "Automatic",
            percentage=self.check_percentage,
        )
