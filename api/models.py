"""Specification of classes used within the API."""
import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone


def create_id() -> uuid.UUID:
    """
    Create a random UUID through using the uuid library.

    :return: the random UUID
    """
    return uuid.uuid4()


class Submission(models.Model):
    """
    Submission which is to be transcribed.

    Note that it is possible that multiple Transcriptions link to the same
    Submission due to the transcription exceeding the maximum length of the
    Transcription's completion method (e.g. the transcription is bigger than
    9000 characters on Reddit. Hence the complete transcription is spread over
    multiple Reddit comments, which are saved in the API as Transcriptions).
    """

    """
    The ID of the Submission on the "source" platform.

    Note that this field is not used as a primary key and hence the database
    also keeps an underlying "id" field which is the primary key.
    """
    submission_id = models.CharField(max_length=36, default=create_id)

    """The time the Submission is submitted."""
    submission_time = models.DateTimeField(default=timezone.now)

    """
    The ID of the Submission in the old Redis database.

    Note that this field is only used for handling the redis changeover and
    can be removed afterwards.
    """
    redis_id = models.CharField(max_length=12, blank=True, null=True)

    """The BlossomUser who has claimed the Submission."""
    claimed_by = models.ForeignKey(
        "authentication.BlossomUser",
        on_delete=models.CASCADE,
        related_name="claimed_by",
        null=True,
        blank=True,
    )

    """The BlossomUser who has completed the Submission."""
    completed_by = models.ForeignKey(
        "authentication.BlossomUser",
        on_delete=models.CASCADE,
        related_name="completed_by",
        null=True,
        blank=True,
    )

    """The time at which the Submission is claimed."""
    claim_time = models.DateTimeField(default=None, null=True, blank=True)

    """The time at which the Submission is claimed."""
    complete_time = models.DateTimeField(default=None, null=True, blank=True)

    """
    The source platform from which the Submission originates.

    Note that the "submission_id" is related to this field as described in its
    documentation.
    """
    source = models.CharField(max_length=20)

    """
    The URL to the Submission directly on its source.

    Note that the maximum length is derived from https://stackoverflow.com/a/219664
    """
    url = models.CharField(max_length=2083, null=True, blank=True)

    """The URL to the Submission on /r/TranscribersOfReddit."""
    tor_url = models.CharField(max_length=2083, null=True, blank=True)

    """Whether the post has been archived, for example by /u/tor_archivist."""
    archived = models.BooleanField(default=False)

    def __str__(self) -> str:
        """
        Retrieve the String representation of the Submission object.

        :return: the String representation of the Submission
        """
        return f"{self.submission_id}"

    @property
    def has_ocr_transcription(self) -> bool:
        """
        Whether the Submission has an OCR transcription.

        This property is determined by checking whether a Transcription by the
        user "transcribot" exists for the Submission.

        :return: whether the Submission has an OCR transcription
        """
        # lazy load transcription model
        return bool(
            Transcription.objects.filter(
                Q(submission=self) & Q(author__username="transcribot")
            )
        )


class Transcription(models.Model):
    """
    The transcription of a Submission.

    Note that one instance of the Transcription can possibly be a partial
    transcription of a Submission, where the complete transcription can be
    aggregated by combining the multiple Transcription instances with the same
    "submission". As explained in the Submission class, this can be due to the
    complete transcription exceeding the maximum allowed length of the
    "completion_method".
    """

    """The Submission for which the Transcription is made."""
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)

    """The BlossomUser who has authored of the Transcription."""
    author = models.ForeignKey("authentication.BlossomUser", on_delete=models.CASCADE)

    """The time the Transcription has been created."""
    post_time = models.DateTimeField(default=timezone.now)
    # reddit comment ID or similar

    """
    The ID of the Transcription on the "completion_method" platform.

    Note that this field is not used as a primary key and hence the database
    also keeps an underlying "id" field which is the primary key.
    """
    transcription_id = models.CharField(max_length=36)
    # "reddit", "api", "blossom". Leaving extra characters in case we want
    # to expand the options.

    """The platform from which the Transcription originates."""
    completion_method = models.CharField(max_length=20)

    """The URL to the Transcription on the source platform."""
    url = models.CharField(max_length=2083, null=True, blank=True)

    """
    The text of the transcription.

    The SQL longtext type is forced, as per https://stackoverflow.com/a/23169977
    """
    text = models.TextField(max_length=4_294_000_000, null=True, blank=True)

    """
    The text of the transcription, created by OCR.

    Note that either "text" or "ocr_text" is null.
    """
    ocr_text = models.TextField(max_length=4_294_000_000, null=True, blank=True)

    """
    Whether the Transcription is removed from Reddit.

    This is mostly to keep track of the Reddit spam filter, as sometimes it
    filters the posts as spam. Gladly this does not impact our validation,
    as we can still access it through workarounds.
    """
    removed_from_reddit = models.BooleanField(default=False)

    def __str__(self) -> str:
        """
        Retrieve the String representation of the Transcription object.

        :return: the String representation of the Transcription
        """
        return f"{self.submission} by {self.author.username}"
