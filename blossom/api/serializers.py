from rest_framework import serializers
from django.contrib.auth.models import User

from blossom.api.models import Submission, Transcription, Volunteer


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ("username",)


class VolunteerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Volunteer
        fields = (
            "id",
            "username",
            "gamma",
            "join_date",
            "last_login_time",
            "accepted_coc"
        )


class SubmissionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Submission
        fields = (
            "id",
            "submission_id",
            "claimed_by",
            "completed_by",
            "claim_time",
            "complete_time",
            "source",
            "url",
        )


class TranscriptionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Transcription
        fields = (
            "submission",
            "author",
            "transcription_id",
            "completion_method",
            "url",
            "text",
        )
