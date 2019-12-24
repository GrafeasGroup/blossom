from rest_framework import serializers
from django.contrib.auth.models import User

from tor_app.database.models import Post
from tor_app.database.models import Transcription
from tor_app.database.models import Volunteer


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


class PostSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Post
        fields = (
            "id",
            "post_id",
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
            "post",
            "author",
            "transcription_id",
            "completion_method",
            "url",
            "text",
        )
