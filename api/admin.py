"""Configuration for the admin interface of Django."""
from django.contrib import admin

from api.models import Submission, Transcription

# Register your models here.
admin.site.register(Transcription)
admin.site.register(Submission)
