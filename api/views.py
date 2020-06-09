"""The views of the API, providing the possible API requests."""
import random
import uuid
from datetime import timedelta
from typing import Dict

import pytz
from django.conf import settings
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_yasg.openapi import Parameter
from drf_yasg.openapi import Response as DocResponse
from drf_yasg.openapi import Schema
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import AdminApiKeyCustomCheck
from api.helpers import validate_request
from api.models import Source, Submission, Transcription
from api.serializers import (
    SourceSerializer,
    SubmissionSerializer,
    TranscriptionSerializer,
    VolunteerSerializer,
)
from api.slack_helpers import client as slack
from authentication.models import BlossomUser
