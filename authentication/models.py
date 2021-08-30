"""Models used within the Authentication application."""
from typing import Any

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework_api_key.models import APIKey

from api.models import Submission


class BlossomUserManager(UserManager):
    # https://stackoverflow.com/a/7774039
    def filter(self, **kwargs: Any) -> QuerySet:
        """Override `filter` to make usernames case insensitive."""
        if "username" in kwargs:
            kwargs["username__iexact"] = kwargs["username"]
            del kwargs["username"]
        return super().filter(**kwargs)

    def get(self, **kwargs: Any) -> QuerySet:
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

    objects = BlossomUserManager()

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
        return Submission.objects.filter(completed_by=self).count()

    def __str__(self) -> str:
        return self.username

    def get_rank(self, override: int = None) -> str:
        """
        Return the name of the volunteer's current rank.

        Override provided for the purposes of checking ranks.
        """
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
