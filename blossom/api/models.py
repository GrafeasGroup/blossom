"""Specification of classes used within the API."""
import logging
import uuid
from typing import Any, Optional
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from blossom.api.slack import client
from blossom.ocr.errors import OCRError
from blossom.ocr.helpers import escape_reddit_links, process_image, replace_shortlinks


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

    class Meta:
        indexes = [models.Index(fields=["url", "tor_url"])]

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

    # The title of the submission.
    title = models.CharField(max_length=300, blank=True, null=True)

    # The URL to the Submission directly on its source.
    url = models.URLField(null=True, blank=True)

    # The URL to the Submission on /r/TranscribersOfReddit.
    tor_url = models.URLField(null=True, blank=True)

    # Whether the post has been archived, for example by /u/tor_archivist.
    archived = models.BooleanField(default=False)

    # A link to the content that the submission is about. An image, audio, video, etc.
    # If this is an image, it is sent to ocr.space for automatic transcription.
    content_url = models.URLField(null=True, blank=True)

    # If this is from Reddit, then it mirrors the status on Reddit's side that we get
    # from PRAW. Otherwise it can be set manually to mark something that shouldn't be
    # shown without a cover.
    nsfw = models.BooleanField(null=True, blank=True)  # maps to PRAW's `.over_18`

    # We need to keep track of every submission that we come across, but there
    # will always be content that needs to be removed from the hands of our volunteers
    # because of various reasons (rule-breaking content on other subs, something that
    # got posted that shouldn't have, etc.). This is used by the unclaim feature
    # specifically.
    removed_from_queue = models.BooleanField(default=False)

    # Whether the submission has been approved by the moderators.
    # If this is set to True, no new reports should be generated for this submission.
    approved = models.BooleanField(default=False)

    # If the submission has been reported, this contains the report reason
    report_reason = models.CharField(max_length=300, null=True, blank=True)
    # If the submission has been reported, this contains the info to get
    # the report message on Slack
    report_slack_channel_id = models.CharField(max_length=50, null=True, blank=True)
    report_slack_message_ts = models.CharField(max_length=50, null=True, blank=True)

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

    @property
    def has_slack_report_message(self) -> bool:
        """Determine whether a Slack report message exists for this submission."""
        return (
            self.report_slack_channel_id is not None
            and self.report_slack_message_ts is not None
        )

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
        # TODO: add @send_to_worker decorator to queue this
        if not settings.ENABLE_OCR:
            logging.warning("OCR is disabled; this call has been ignored.")
            return
        if self.cannot_ocr:
            logging.info("Submission already marked with `cannot_ocr`; skipping.")
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
            result["text"] = replace_shortlinks(result["text"])

        self._create_ocr_transcription(text=result["text"])

    def save(self, *args: Any, skip_extras: bool = False, **kwargs: Any) -> None:
        """
        Save the submission object.

        The submission must be saved before the OCR is run, because otherwise
        we'd assign an unsaved object as the other end of the foreign key for
        the new transcription. This is an annoying bug to track down, so make
        sure that you save the submission before actually creating anything
        that relates to it.

        If `skip_extras` is set, then it should bypass everything that is not
        simply "save the object to the db".
        """
        super(Submission, self).save(*args, **kwargs)
        if not skip_extras:
            if self.is_image and not self.has_ocr_transcription:
                # TODO: This is a great candidate for a basic queue system
                self.generate_ocr_transcription()

    def get_subreddit_name(self) -> str:
        """
        Return the subreddit name.

        Once we get everything transitioned to sources, this will continue to
        work. In the meantime, we can pull the subreddit from the urls.
        """
        if self.source.name != "reddit":
            return self.source.name
        return f'/r/{self.url.split("/r/")[1].split("/")[0]}'


class Transcription(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=["author"], name="author_idx"),
            models.Index(fields=["submission"], name="submission_idx"),
            models.Index(fields=["original_id"], name="original_id_idx"),
            models.Index(fields=["url"], name="url_idx"),
        ]

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


class TranscriptionCheck(models.Model):
    class TranscriptionCheckStatus(models.TextChoices):
        # The default. The check needs to be claimed by a moderator.
        PENDING = "pending"
        # The transcription has been approved by the moderator.
        APPROVED = "approved"
        # The moderator left a comment for the user to fix minor errors (e.g. formatting)
        # and is waiting for them to fix them.
        COMMENT_PENDING = "comment_pending"
        # The moderator left a comment and the user has fixed the errors.
        COMMENT_RESOLVED = "comment_resolved"
        # The moderator left a comment and the user has NOT fixed the errors.
        COMMENT_UNFIXED = "comment_unfixed"
        # The moderator discovered major errors (e.g. a PI violation) and  is waiting
        # for the user to fix them (e.g. delete the transcription).
        WARNING_PENDING = "warning_pending"
        # The moderator warned the user and they responded and resolved any issues,
        # if applicable.
        WARNING_RESOLVED = "warning_resolved"
        # The moderator warned the user and they didn't respond or resolve the issues.
        WARNING_UNFIXED = "warning_unfixed"

    # The Transcription for which the check is made.
    transcription = models.ForeignKey(Transcription, on_delete=models.CASCADE)

    # The moderator assigned to this check
    moderator = models.ForeignKey(
        "authentication.BlossomUser",
        default=None,
        null=True,
        on_delete=models.SET_DEFAULT,
    )

    # The current status of the check
    status = models.CharField(
        max_length=20,
        choices=TranscriptionCheckStatus.choices,
        default=TranscriptionCheckStatus.PENDING,
    )

    # The trigger for the check.
    # Can be something like "Low activity", "Watched (70.0%)", etc.
    trigger = models.CharField(max_length=200, null=True)

    # An internal note for the moderators
    internal_note = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        default=None,
    )

    # The time the check has been created.
    create_time = models.DateTimeField(default=timezone.now)
    # The time that the check has been claimed by a moderator
    claim_time = models.DateTimeField(default=None, null=True, blank=True)
    # The time that the check has been fully resolved
    complete_time = models.DateTimeField(default=None, null=True, blank=True)

    # The info needed to update the Slack message of the check
    slack_channel_id = models.CharField(
        max_length=50, default=None, null=True, blank=True
    )
    slack_message_ts = models.CharField(
        max_length=50, default=None, null=True, blank=True
    )

    def get_slack_url(self) -> Optional[str]:
        """Get the permalink for the check on Slack."""
        if not self.slack_channel_id or not self.slack_message_ts:
            return None

        url_response = client.chat_getPermalink(
            channel=self.slack_channel_id,
            message_ts=self.slack_message_ts,
        )

        if not url_response.get("ok"):
            return None

        return url_response.get("permalink")


class AccountMigration(models.Model):
    create_time = models.DateTimeField(default=timezone.now)
    old_user = models.ForeignKey(
        "authentication.BlossomUser",
        on_delete=models.SET_NULL,
        related_name="old_user",
        null=True,
        blank=True,
    )
    new_user = models.ForeignKey(
        "authentication.BlossomUser",
        on_delete=models.SET_NULL,
        related_name="new_user",
        null=True,
        blank=True,
    )
    # keep track of submissions that were modified in case we need to roll back
    affected_submissions = models.ManyToManyField(Submission)
    # who has approved this migration?
    moderator = models.ForeignKey(
        "authentication.BlossomUser",
        default=None,
        null=True,
        on_delete=models.SET_DEFAULT,
    )
    # The info needed to update the Slack message of the check
    slack_channel_id = models.CharField(
        max_length=50, default=None, null=True, blank=True
    )
    slack_message_ts = models.CharField(
        max_length=50, default=None, null=True, blank=True
    )

    def perform_migration(self) -> None:
        """Move all submissions attributed to one account to another."""
        existing_submissions = Submission.objects.filter(completed_by=self.old_user)
        self.affected_submissions.add(*existing_submissions)

        # need to process transcriptions first because the submissions they're
        # linked to are about to change
        transcriptions = Transcription.objects.filter(
            submission__in=existing_submissions, author=self.old_user
        )
        transcriptions.update(author=self.new_user)
        existing_submissions.update(
            claimed_by=self.new_user, completed_by=self.new_user
        )

    def revert(self) -> None:
        """Undo the account migration."""
        transcriptions = Transcription.objects.filter(
            submission__in=self.affected_submissions.all(), author=self.new_user
        )
        transcriptions.update(author=self.old_user)
        self.affected_submissions.update(
            claimed_by=self.old_user, completed_by=self.old_user
        )
