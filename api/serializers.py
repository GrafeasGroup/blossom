"""Serializers for the model classes used within the API."""
from django.contrib.auth.models import User
from rest_framework import serializers

from api.models import Submission, Transcription
from authentication.models import BlossomUser


class UserSerializer(serializers.HyperlinkedModelSerializer):
    """The Serializer for the User class."""

    class Meta:
        """The Meta class to describe the class and fields to serialize."""

        model = User
        fields = ("username",)


class VolunteerSerializer(serializers.HyperlinkedModelSerializer):
    """The Serializer for the BlossomUser class."""

    class Meta:
        """The Meta class to describe the class and fields to serialize."""

        model = BlossomUser
        fields = (
            "id",
            "username",
            "gamma",
            "date_joined",
            "last_login",
            "accepted_coc",
            "blacklisted",
        )


class SubmissionSerializer(serializers.HyperlinkedModelSerializer):
    """The Serializer for the Submission class."""

    claimed_by = serializers.HyperlinkedRelatedField(
        view_name="volunteer-detail", read_only=True
    )
    completed_by = serializers.HyperlinkedRelatedField(
        view_name="volunteer-detail", read_only=True
    )

    class Meta:
        """The Meta class to describe the class and fields to serialize."""

        model = Submission
        fields = (
            "id",
            "submission_id",
            "submission_time",
            "claimed_by",
            "completed_by",
            "claim_time",
            "complete_time",
            "source",
            "url",
            "tor_url",
            "has_ocr_transcription",
            "archived",
        )


class TranscriptionSerializer(serializers.HyperlinkedModelSerializer):
    """The Serializer for the Transcription class."""

    author = serializers.HyperlinkedRelatedField(
        view_name="volunteer-detail", read_only=True
    )

    class Meta:
        """The Meta class to describe the class and fields to serialize."""

        model = Transcription
        fields = (
            "id",
            "submission",
            "author",
            "transcription_id",
            "completion_method",
            "url",
            "text",
            "ocr_text",
            "removed_from_reddit",
        )
