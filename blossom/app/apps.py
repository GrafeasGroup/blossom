from django.apps import AppConfig as AC


class AppConfig(AC):
    default_auto_field = "django.db.models.BigAutoField"
    name = "blossom.app"
