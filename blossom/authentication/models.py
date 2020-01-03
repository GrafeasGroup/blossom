from django.contrib.auth.models import AbstractUser
from django.db import models
from rest_framework_api_key.models import APIKey

from blossom.api.models import Transcription


class BlossomUser(AbstractUser):
    backend = "blossom.authentication.backends.EmailBackend"

    is_grafeas_staff = models.BooleanField(default=False)
    api_key = models.OneToOneField(
        APIKey, on_delete=models.CASCADE, null=True, blank=True
    )
    is_volunteer = models.BooleanField(default=True)
    accepted_coc = models.BooleanField(default=False)

    @property
    def gamma(self):
        return Transcription.objects.filter(author=self).count()

    def __str__(self):
        return self.username
