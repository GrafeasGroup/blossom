"""Configuration for the admin interface of Django."""
from django.contrib import admin

from blossom.api.models import Submission, Transcription


class SubmissionAdmin(admin.ModelAdmin):
    search_fields = ("id", "original_id", "title", "url", "tor_url")


# Register your models here.
admin.site.register(Transcription)
admin.site.register(Submission, SubmissionAdmin)
