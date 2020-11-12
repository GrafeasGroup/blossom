"""Specification of classes used within the API."""
import logging
import uuid
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from ocr.errors import OCRError
from ocr.helpers import escape_reddit_links, process_image


def create_id() -> uuid.UUID:  # pragma: no cover
    """
    Create a random UUID for elements as needed.

    Sometimes we won't have the original ID of transcriptions or submissions,
    so instead we fake them using UUIDs. For example, this is used when
    creating dummy transcriptions or submissions due to incomplete data from
    the Redis transition over 2019-20. Excluded from testing because this is
    just a wrapper for the standard library.

    :return: the random UUID
    """
    return uuid.uuid4()


class Source(models.Model):
    """
    The source that the particular Submission or Transcription came from.

    The majority of these will be "reddit", but to save on space and more easily
    standardize we have the option of including other sources as we grow.
    """

    # Name of the origin of the content. For example: reddit, blossom, etc.
    name = models.CharField(max_length=36, primary_key=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


def get_default_source() -> str:
    """
    Grabs the proper default ID for submissions and transcriptions.

    Django cannot serialize lambda functions, so we need to have a helper
    function to handle the default action of the `source` foreign keys.

    Right now, all of our content comes from Reddit, so we have that set
    as the default source. Should this ever change, we can simply update
    this function and be good to go.

    :return: the ID of Source record for reddit
    """
    obj, _ = Source.objects.get_or_create(name="reddit")
    return obj.name


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
    # "id" field is the primary key. Also note that this is not named
    # "source_id" because of internal conflicts with the `source` FK.
    original_id = models.CharField(max_length=36, default=create_id)

    # The time the Submission was created.
    create_time = models.DateTimeField(default=timezone.now)

    # The time the Submission was last updated.
    last_update_time = models.DateTimeField(default=timezone.now)

    # The ID of the Submission in the old Redis database.
    # This field is only used for handling the redis changeover and
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

    # The source platform from which the Submission originates.
    source = models.ForeignKey(
        Source, default=get_default_source, on_delete=models.CASCADE
    )

    # The URL to the Submission directly on its source.
    url = models.URLField(null=True, blank=True)

    # The URL to the Submission on /r/TranscribersOfReddit.
    tor_url = models.URLField(null=True, blank=True)

    # Whether the post has been archived, for example by /u/tor_archivist.
    archived = models.BooleanField(default=False)

    # A link to the content that the submission is about. An image, audio, video, etc.
    # If this is an image, it is sent to ocr.space for automatic transcription.
    content_url = models.URLField(null=True, blank=True)

    # We need to keep track of every submission that we come across, but there
    # will always be content that needs to be removed from the hands of our volunteers
    # because of various reasons (rule-breaking content on other subs, something that
    # got posted that shouldn't have, etc.). This is used by the unclaim feature
    # specifically.
    removed_from_queue = models.BooleanField(default=False)

    # If we get errors back from our OCR solution or if a given submission cannot
    # be run through OCR, this flag should be set.
    cannot_ocr = models.BooleanField(default=False)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.original_id}"

    @property
    def has_ocr_transcription(self) -> bool:
        """
        Whether the Submission has an OCR transcription.

        This property is determined by checking whether a Transcription by the
        user "transcribot" exists for the Submission.

        :return: whether the Submission has an OCR transcription
        """
        return (
            False
            if self.cannot_ocr
            else bool(
                Transcription.objects.filter(
                    submission=self, author__username="transcribot"
                )
            )
        )

    @property
    def is_image(self) -> bool:
        """Check whether the content url is from an image host we recognize."""
        return urlparse(self.content_url).netloc in settings.IMAGE_DOMAINS

    def _create_ocr_transcription(self, text: str) -> None:
        """
        Handle creation of an OCR transcription in a testable way.

        This function creates a transcription object, but deliberately leaves
        `original_id` out because it will be handled with a patch call from
        transcribot after it's processed.
        """
        Transcription.objects.create(
            submission=self,
            author=get_user_model().objects.get(username="transcribot"),
            source=Source.objects.get(name="blossom"),
            text=text,
        )

    def generate_ocr_transcription(self) -> None:
        """Create automatic OCR transcriptions of images."""
        if not settings.ENABLE_OCR:
            logging.warning("OCR is disabled; this call has been ignored.")
            return

        try:
            result = process_image(self.content_url)
        except OCRError as e:
            logging.warning(
                "There was an error in generating the OCR transcription: " + str(e)
            )
            self.cannot_ocr = True
            return

        if not result:
            self.cannot_ocr = True
            return

        if self.source.name == "reddit":
            result["text"] = escape_reddit_links(result["text"])

        self._create_ocr_transcription(text=result["text"])

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Save the submission object.

        The submission must be saved before the OCR is run, because otherwise
        we'd assign an unsaved object as the other end of the foreign key for
        the new transcription. This is an annoying bug to track down, so make
        sure that you save the submission before actually creating anything
        that relates to it.
        """
        super(Submission, self).save(*args, **kwargs)
        if self.is_image and not self.has_ocr_transcription:
            # TODO: This is a great candidate for a basic queue system
            self.generate_ocr_transcription()


class Transcription(models.Model):
    # The Submission for which the Transcription is made.
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)

    # The BlossomUser who has authored the Transcription.
    author = models.ForeignKey("authentication.BlossomUser", on_delete=models.CASCADE)

    # The time the Transcription has been created.
    create_time = models.DateTimeField(default=timezone.now)
    # The time the Transcription was last updated.
    last_update_time = models.DateTimeField(default=timezone.now)

    # The ID of the Transcription on the "source" platform.
    # Note that this field is not used as a primary key; an underlying
    # "id" field is the primary key. This is not named "source_id"
    # because of internal conflicts with the `source` FK.
    # If this field is null, that means that it's a transcribot post
    # that hasn't actually been posted yet and we don't have the patch
    # call to add this field. All transcriptions that come in from other
    # places (ToR, the transcription app, etc) should have this field.
    original_id = models.CharField(max_length=36, blank=True, null=True)

    # The platform from which the Transcription originates.
    source = models.ForeignKey(
        Source,
        default=get_default_source,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_related",
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

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.submission} by {self.author.username}"
