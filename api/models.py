"""Specification of classes used within the API."""
import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone


def create_id() -> uuid.UUID:
    """
    Create a random UUID through using the uuid library so that we can fake
    source IDs if needed; for example, when creating dummy transcriptions or
    submissions due to incomplete data from the Redis transition over 2019-20.

    :return: the random UUID
    """
    return uuid.uuid4()


class Source(models.Model):
    """
    The source that the particular Submission or Transcription came from. The
    majority of these will be "reddit", but to save on space and more easily
    standardize we have the option of including other sources as we grow.
    """

    # Where did our content come from?
    name = models.CharField(max_length=20)

    def __str__(self) -> str:
        return self.name


def get_reddit_source() -> int:
    """
    Grabs the proper default ID for submissions and transcriptions.

    Django cannot serialize lambda functions, so we need to have a helper
    function to handle the default action of the `source` foreign keys.

    :return: the ID of the Source record for reddit
    """
    return Source.objects.get(name="reddit").id


class Submission(models.Model):
    """
    Submission which is to be transcribed.

    Note that it is possible that multiple Transcriptions link to the same
    Submission due to multiple users possibly transcribing the same Submission.
    An OCR transcription as well as a human transcription can be seen as a
    common example of this phenomenon.
    """

    # The ID of the Submission on the "source" platform.
    # Note that this field is not used as a primary key; an underlying
    # "id" field is the primary key. Note: this is not named "source_id"
    # because of internal conflicts with the `source` FK.
    original_id = models.CharField(max_length=36, default=create_id)

    # The time the Submission is submitted.
    create_time = models.DateTimeField(default=timezone.now)
    last_update_time = models.DateTimeField(default=timezone.now)

    # The ID of the Submission in the old Redis database.
    # Note that this field is only used for handling the redis changeover and
    # can be removed afterwards.
    redis_id = models.CharField(max_length=12, blank=True, null=True)

    # The BlossomUser who has claimed the Submission.
    claimed_by = models.ForeignKey(
        "authentication.BlossomUser",
        on_delete=models.CASCADE,
        related_name="claimed_by",
        null=True,
        blank=True,
    )

    # The BlossomUser who has completed the Submission.
    completed_by = models.ForeignKey(
        "authentication.BlossomUser",
        on_delete=models.CASCADE,
        related_name="completed_by",
        null=True,
        blank=True,
    )

    # The time at which the Submission is claimed.
    claim_time = models.DateTimeField(default=None, null=True, blank=True)

    # The time at which the Submission is completed.
    complete_time = models.DateTimeField(default=None, null=True, blank=True)

    # The source platform from which the Submission originates
    source = models.ForeignKey(
        Source, default=get_reddit_source, on_delete=models.CASCADE
    )

    # The URL to the Submission directly on its source.
    url = models.URLField(null=True, blank=True)

    # The URL to the Submission on /r/TranscribersOfReddit.
    tor_url = models.URLField(null=True, blank=True)

    # Whether the post has been archived, for example by /u/tor_archivist
    archived = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.source_id}"

    @property
    def has_ocr_transcription(self) -> bool:
        """
        Whether the Submission has an OCR transcription.

        This property is determined by checking whether a Transcription by the
        user "transcribot" exists for the Submission.

        :return: whether the Submission has an OCR transcription
        """
        return bool(
            Transcription.objects.filter(
                Q(submission=self) & Q(author__username="transcribot")
            )
        )


class Transcription(models.Model):
    # The Submission for which the Transcription is made
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)

    # The BlossomUser who has authored the Transcription
    author = models.ForeignKey("authentication.BlossomUser", on_delete=models.CASCADE)

    # The time the Transcription has been created
    create_time = models.DateTimeField(default=timezone.now)
    last_update_time = models.DateTimeField(default=timezone.now)

    # The ID of the Transcription on the "source" platform.
    # Note that this field is not used as a primary key; an underlying
    # "id" field is the primary key. Note: this is not named "source_id"
    # because of internal conflicts with the `source` FK.
    original_id = models.CharField(max_length=36)

    # The platform from which the Transcription originates.
    source = models.ForeignKey(
        Source, default=get_reddit_source, on_delete=models.CASCADE
    )

    # The URL to the Transcription on the source platform.
    url = models.URLField(null=True, blank=True)

    # The text of the transcription. We force the SQL longtext type, per
    # https://stackoverflow.com/a/23169977.
    text = models.TextField(max_length=4_294_000_000, null=True, blank=True)

    # Whether the Transcription is removed from Reddit.
    # This is mostly to keep track of the behavior of the Reddit spam filter,
    # as this filter sometimes marks the transcriptions falsely as spam. This
    # does not affect our validation as we can still access the transcription
    # through workarounds.
    removed_from_reddit = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.submission} by {self.author.username}"
