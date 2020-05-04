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
    is_volunteer = models.BooleanField(default=True)
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
        return Transcription.objects.filter(author=self).count()

    def __str__(self) -> str:
        return self.username
