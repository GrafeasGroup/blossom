from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from rest_framework_api_key.models import APIKey

from api.models import Transcription


class BlossomUser(AbstractUser):
    backend = "authentication.backends.EmailBackend"

    # abstract out to role / permission / group
    is_volunteer = models.BooleanField(default=True)
    is_grafeas_staff = models.BooleanField(default=False)

    api_key = models.OneToOneField(
        APIKey, on_delete=models.CASCADE, null=True, blank=True
    )

    last_update_time = models.DateTimeField(default=timezone.now)
    accepted_coc = models.BooleanField(default=False)
    blacklisted = models.BooleanField(default=False)

    @property
    def gamma(self):
        return Transcription.objects.filter(author=self).count()

    def __str__(self):
        return self.username
