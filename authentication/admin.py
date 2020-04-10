"""Configuration for the admin interface of Django."""
from django.contrib import admin
from authentication.models import BlossomUser

# Register your models here.
admin.site.register(BlossomUser)
