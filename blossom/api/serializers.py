"""
Serializers for the model classes used within the API.

These serializers are used to generate a dictionary from a specific model. The
fields and model used per serializer are specified in the Meta class included
within the serializer. This serialized object can in turn be used for serving
objects through the API.
"""
from typing import Any

from django.contrib.auth.models import User
from rest_framework import serializers

from blossom.api.models import Source, Submission, Transcription
from blossom.authentication.models import BlossomUser


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
            "last_update_time",
            "accepted_coc",
            "blocked",
            "is_bot",
        )


class SourceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Source
        fields = ("name",)


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
            "original_id",
            "create_time",
            "last_update_time",
            "claimed_by",
            "completed_by",
            "claim_time",
            "complete_time",
            "source",
            "title",
            "nsfw",
            "url",
            "tor_url",
            "content_url",
            "has_ocr_transcription",
            "transcription_set",
            "archived",
            "cannot_ocr",
            "redis_id",
            "removed_from_queue",
        )
        # TODO: Omitting the below line while adding `transcription_set` makes
        # a call to a single submission created with the test data set take
        # ~_15.3 seconds_. If we mark just that field as read-only, the page
        # render time drops to ~0.1 seconds.
        #
        # WTF‽
        read_only_fields = ["transcription_set"]


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
            "create_time",
            "last_update_time",
            "original_id",
            "source",
            "url",
            "text",
            "removed_from_reddit",
        )


class FindResponseSerializer(serializers.Serializer):
    """Serializer for the response of the /find/ endpoint.

    See https://www.django-rest-framework.org/api-guide/serializers/
    """

    # We just delegate to the serializers of the models
    submission = SubmissionSerializer()
    author = VolunteerSerializer(required=False)
    transcription = TranscriptionSerializer(required=False)
    ocr = TranscriptionSerializer(required=False)

    # We cannot type this properly without circular imports
    def create(self, validated_data: Any) -> Any:
        """Create an object based on the validated data."""
        submission = validated_data.get("submission")
        author = validated_data.get("author", None)
        transcription = validated_data.get("transcription", None)
        ocr = validated_data.get("ocr", None)

        return {
            "submission": Submission(**submission),
            "author": BlossomUser(**author) if author else None,
            "transcription": Transcription(**transcription) if transcription else None,
            "ocr": Transcription(**ocr) if ocr else None,
        }

    # We cannot type this properly without circular imports
    def update(self, instance: Any, validated_data: Any) -> Any:
        """Update the object based on the validated data."""
        instance.submission = validated_data.get("submission")
        instance.author = validated_data.get("author", None)
        instance.transcription = validated_data.get("transcription", None)
        instance.ocr = validated_data.get("ocr", None)
        return instance
