import uuid

import pytz
from django.db import models
from django.utils import timezone
from rest_framework_api_key.models import APIKey
from django.contrib.auth.hashers import make_password, check_password

from blossom.authentication.custom_user import BlossomUser

class Submission(models.Model):
    # It is rare, but possible, for a post to have more than one transcription.
    # Therefore, posts are separate from transcriptions, but there will almost
    # always be one transcription per post.

    def create_id(self):
        return uuid.uuid4()

    submission_id = models.CharField(max_length=36, default=create_id)
    post_time = models.DateTimeField(default=timezone.now)
    claimed_by = models.ForeignKey(
        "Volunteer",
        on_delete=models.CASCADE,
        related_name="claimed_by",
        null=True,
        blank=True,
    )
    # This is only for handling the redis changeover
    redis_id = models.CharField(max_length=12, blank=True, null=True)
    completed_by = models.ForeignKey(
        "Volunteer",
        on_delete=models.CASCADE,
        related_name="completed_by",
        null=True,
        blank=True,
    )

    # obviously these should be the same, but it makes it a lot easier to
    # perform checks as to who claimed so that we don't have to query reddit
    claim_time = models.DateTimeField(default=None, null=True, blank=True)
    complete_time = models.DateTimeField(default=None, null=True, blank=True)

    # Where does it come from? Reddit? A library?
    source = models.CharField(max_length=20)
    # recommended max length https://stackoverflow.com/a/219664
    url = models.CharField(max_length=2083, null=True, blank=True)
    tor_url = models.CharField(max_length=2083, null=True, blank=True)

    def __str__(self):
        return f"{self.submission_id}"


class Transcription(models.Model):

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    author = models.ForeignKey("Volunteer", on_delete=models.CASCADE)
    post_time = models.DateTimeField(default=timezone.now)
    # reddit comment ID or similar
    transcription_id = models.CharField(max_length=36)
    # "reddit", "api", "blossom". Leaving extra characters in case we want
    # to expand the options.
    completion_method = models.CharField(max_length=20)
    url = models.CharField(max_length=2083, null=True, blank=True)
    # force SQL longtext type, per https://stackoverflow.com/a/23169977
    text = models.TextField(max_length=4_294_000_000)
    ocr_text = models.TextField(max_length=4_294_000_000, null=True, blank=True)
    # sometimes posts get stuck in the spam filter. We can still validate those,
    # but it takes some effort. It is good to store the fact that it was
    # removed, even if we can still access it through workarounds, just so we
    # can keep a running tally on the reddit spam filter. This will become
    # increasingly less useful as we move into new territories, but it's still
    # a useful field for now.
    removed_from_reddit = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.submission} by {self.author.username}"


class Volunteer(models.Model):
    accepted_coc = models.BooleanField(default=False)
    join_date = models.DateTimeField(default=timezone.now)
    last_login_time = models.DateTimeField(default=None, null=True, blank=True)
    api_key = models.OneToOneField(
        APIKey, on_delete=models.CASCADE, null=True, blank=True
    )
    username = models.CharField(max_length=150)
    password = models.CharField(max_length=100, default=None, null=True, blank=True)
    staff_account = models.OneToOneField(
        BlossomUser, on_delete=models.CASCADE, null=True, blank=True
    )

    def set_password(self, password):
        self.password = make_password(password)

    def check_password(self, password):
        return check_password(self.password, password)

    def set_unusable_password(self):
        # Set a value that will never be a valid hash
        self.password = make_password(None)

    def is_staff(self):
        return self.staff_account != None

    def __str__(self):
        # noinspection PyUnresolvedReferences
        return f"{self.user.username}"

    @property
    def gamma(self):
        return Transcription.objects.filter(author=self).count()


class Summary(object):
    """
    A basic object that just generates a summary view that's easy to access.
    """
    def generate_summary(self):

        # subtract 1 from volunteer count for anon volunteer
        return {
            'volunteer_count': Volunteer.objects.count(),
            'transcription_count': Transcription.objects.count(),
            'days_since_inception': (
                timezone.now() - pytz.timezone("UTC").localize(
                    timezone.datetime(day=1, month=4, year=2017),
                    is_dst=None
                )
            ).days
        }
