"""
Serializers for the model classes used within the API.

These serializers are used to generate a JSON object from a specific model. The
fields and model used per serializer are specified in the Meta class included
within the serializer.
"""
from django.contrib.auth.models import User
from rest_framework import serializers

from api.models import Submission, Transcription
from authentication.models import BlossomUser


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ("username",)


class VolunteerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
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
    claimed_by = serializers.HyperlinkedRelatedField(
        view_name="volunteer-detail", read_only=True
    )
    completed_by = serializers.HyperlinkedRelatedField(
        view_name="volunteer-detail", read_only=True
    )

    class Meta:
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
    author = serializers.HyperlinkedRelatedField(
        view_name="volunteer-detail", read_only=True
    )

    class Meta:
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
