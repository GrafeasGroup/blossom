import uuid

from django.apps import apps
from django.db import models
from django.db.models import Q
from django.utils import timezone


def create_id():
    return uuid.uuid4()


class Submission(models.Model):
    # It is rare, but possible, for a post to have more than one transcription.
    # Therefore, posts are separate from transcriptions, but there will almost
    # always be one transcription per post.
    submission_id = models.CharField(max_length=36, default=create_id)
    submission_time = models.DateTimeField(default=timezone.now)

    # This is only for handling the redis changeover
    redis_id = models.CharField(max_length=12, blank=True, null=True)

    # obviously these should be the same, but it makes it a lot easier to
    # perform checks as to who claimed so that we don't have to query reddit
    claimed_by = models.ForeignKey(
        "authentication.BlossomUser",
        on_delete=models.CASCADE,
        related_name="claimed_by",
        null=True,
        blank=True,
    )
    completed_by = models.ForeignKey(
        "authentication.BlossomUser",
        on_delete=models.CASCADE,
        related_name="completed_by",
        null=True,
        blank=True,
    )

    claim_time = models.DateTimeField(default=None, null=True, blank=True)
    complete_time = models.DateTimeField(default=None, null=True, blank=True)

    # Where does it come from? Reddit? A library?
    source = models.CharField(max_length=20)
    # recommended max length https://stackoverflow.com/a/219664
    url = models.CharField(max_length=2083, null=True, blank=True)
    tor_url = models.CharField(max_length=2083, null=True, blank=True)
    # has a completed post been handled by tor_archivist?
    archived = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.submission_id}"

    @property
    def has_ocr_transcription(self):
        # lazy load transcription model
        T = apps.get_model(app_label='api', model_name='Transcription')
        return True if T.objects.filter(
            Q(submission=self) &
            Q(author__username='transcribot')
        ).first() else False


class Transcription(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    author = models.ForeignKey("authentication.BlossomUser", on_delete=models.CASCADE)
    post_time = models.DateTimeField(default=timezone.now)
    # reddit comment ID or similar
    transcription_id = models.CharField(max_length=36)
    # "reddit", "api", "blossom". Leaving extra characters in case we want
    # to expand the options.
    completion_method = models.CharField(max_length=20)
    url = models.CharField(max_length=2083, null=True, blank=True)
    # force SQL longtext type, per https://stackoverflow.com/a/23169977
    text = models.TextField(max_length=4_294_000_000, null=True, blank=True)
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
