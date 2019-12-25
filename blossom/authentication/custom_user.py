from django.contrib.auth.models import AbstractUser

class BlossomUser(AbstractUser):
    backend = 'blossom.authentication.custom_auth.EmailBackend'
