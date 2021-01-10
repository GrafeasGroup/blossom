"""Models used within the Authentication application."""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from rest_framework_api_key.models import APIKey

from api.models import Transcription


class BlossomUser(AbstractUser):
    """
    The user class used within the program.

    Note that this class provides some additional properties based on the current
    status of the user and the roles they fulfill.
    """

    # The backend class which is used to authenticate the BlossomUser.
    backend = "authentication.backends.EmailBackend"

    # TODO: abstract out to role / permission / group
    # A boolean that denotes whether a user account belongs to a volunteer or not.
    is_volunteer = models.BooleanField(default=True)
    # A boolean that denotes whether a user account is a staff account with Grafeas.
    # (not to be confused with the base Django staff account.)
    is_grafeas_staff = models.BooleanField(default=False)

    # Each person is allowed one API key, but advanced security around this
    # means that it is not fully implemented at this time. It is used by
    # u/transcribersofreddit and the other bots, though.
    api_key = models.OneToOneField(
        APIKey, on_delete=models.CASCADE, null=True, blank=True
    )

    # The time that this record was last updated.
    last_update_time = models.DateTimeField(default=timezone.now)
    # Whether this particular user has accepted our Code of Conduct.
    accepted_coc = models.BooleanField(default=False)

    # Whether the user is blacklisted; if so, all bots will refuse to interact
    # with this user.
    blacklisted = models.BooleanField(default=False)

    @property
    def gamma(self) -> int:
        """
        Return the number of transcriptions the user has made.

        Note that this is a calculated property, computed by the number of
        transcriptions in the database.

        :return: the number of transcriptions written by the user.
        """
        if self.blacklisted:
            return 0  # see https://github.com/GrafeasGroup/blossom/issues/15
        return Transcription.objects.filter(author=self).count()

    def get_past_gamma_count(self, delay: int = 5) -> int:
        """
        Return the number of gamma that a user had X seconds ago.

        Defaults to 5 seconds because that's a reasonable delay to make the rank-up
        check work efficiently.

        :param delay: integer; seconds.
        :return: integer; the number of transcriptions written by the user `delay`
            seconds ago.
        """
        delay_time = timezone.now() - timezone.timedelta(seconds=delay)

        return Transcription.objects.filter(
            author=self, create_time__lt=delay_time
        ).count()

    def __str__(self) -> str:
        return self.username

    def get_rank(self, override: int = None) -> str:
        """Return the name of the volunteer's current rank."""
        gamma = override if override else self.gamma

        if gamma >= 10000:
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
        else:
            return "Initiate"
