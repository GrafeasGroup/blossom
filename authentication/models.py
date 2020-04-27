"""Models used within the Authentication application."""
from django.contrib.auth.models import AbstractUser
from django.db import models
from rest_framework_api_key.models import APIKey

from api.models import Transcription


class BlossomUser(AbstractUser):
    """
    The user class used within the program.

    Note that this class provides some additional properties based on the current
    status of the user and the roles they fulfill.
    """

    """The backend class which is used to authenticate the BlossomUser."""
    backend = "authentication.backends.EmailBackend"

    """Whether the user is a staff member of Grafeas."""
    is_grafeas_staff = models.BooleanField(default=False)

    """The API key which the user can use when posting requests to the API."""
    api_key = models.OneToOneField(
        APIKey, on_delete=models.CASCADE, null=True, blank=True
    )

    """Whether the user is a volunteer of Grafeas."""
    is_volunteer = models.BooleanField(default=True)

    """Whether the user has accepted the Code of Conduct."""
    accepted_coc = models.BooleanField(default=False)

    """Whether the user is blacklisted."""
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
