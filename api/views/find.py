from typing import Optional, TypedDict
from urllib.parse import urlparse
from urllib.request import Request

from django.views.decorators.csrf import csrf_exempt
from drf_yasg.openapi import Parameter
from drf_yasg.openapi import Response as DocResponse
from drf_yasg.openapi import Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Submission, Transcription
from authentication.models import BlossomUser


class FindResponse(TypedDict):
    submission: Submission
    transcription: Optional[Transcription]
    author: Optional[BlossomUser]


def normalize_url(reddit_url_str: str) -> Optional[str]:
    """Normalize a Reddit URL to the format that Blossom uses.

    This is necessary because the link could be to Old Reddit, for example.
    """
    parse_result = urlparse(reddit_url_str)
    if "reddit" not in parse_result.netloc:
        return None

    # On Blossom, all URLs end with a slash
    path = parse_result.path

    if not path.endswith("/"):
        path += "/"

    return f"https://reddit.com{path}"


def find_by_submission_url(url: str, url_type: str) -> Optional[FindResponse]:
    """Find the objects by a submission URL."""
    try:
        submission = Submission.objects.get(**{url_type: url})
    except Submission.DoesNotExist:
        return None

    author = submission.completed_by
    if author is not None:
        transcription = submission.transcription_set.filter(author=author)[0]
    else:
        transcription = None

    return {"submission": submission, "author": author, "transcription": transcription}


def find_by_transcription_url(url: str) -> Optional[FindResponse]:
    """Find the objects by a transcription URL."""
    transcription = Transcription.objects.get(url=url)
    author = transcription.author
    submission = transcription.submission

    return {"submission": submission, "author": author, "transcription": transcription}


def find_by_url(url: str) -> Optional[FindResponse]:
    """Find the objects by a normalized URL.

    Example URL:
    https://reddit.com/r/TranscribersOfReddit/comments/plmx5n/curatedtumblr_image_im_an_atheist_but_yall_need/
    """
    url_parts = url.split("/")
    if len(url_parts) == 9:
        # It's a link to a submission
        # Find out if it's a ToR or partner sub submission
        # The fifth segment (index 4) of the link is the sub name
        url_type = "tor_url" if url_parts[4] == "TranscribersOfReddit" else "url"
        return find_by_submission_url(url, url_type)
    elif len(url_parts) == 11:
        # It's a link to a comment
        if url_parts[4] == "TranscribersOfReddit":
            # It's a comment on ToR, e.g. a "claim" comment
            # Extract the ToR submission URL
            submission_url = "/".join(url_parts[:9])
            return find_by_submission_url(submission_url, "tor_url")
        else:
            # It's a comment on a partner sub
            # Check if it's a transcription
            transcription_data = find_by_transcription_url(url)
            if transcription_data is not None:
                return transcription_data
            else:
                # It's some other comment on the partner sub
                # Extract the submission URL and search for that
                submission_url = "/".join(url_parts[:9])
                return find_by_submission_url(submission_url, "url")
    else:
        # Unknown link format
        return None


class FindView(APIView):
    """A view to find submissions or transcriptions by their URL."""

    @csrf_exempt
    @swagger_auto_schema(
        manual_parameters=[
            Parameter(
                "url",
                "query",
                type="string",
                description="The URL to find the object of. "
                "Can be a submission URL, a ToR submission URL or a transcription URL.",
            ),
        ],
        responses={
            200: DocResponse(
                "The URL has been found!",
                schema=Schema(
                    type="object",
                    # TODO: Use the schemas of the corresponding models
                    properties={
                        "submission": Schema(type="object"),
                        "transcription": Schema(type="object"),
                        "author": Schema(type="object"),
                    },
                ),
            ),
            400: "The given URL has an invalid format.",
            404: "The corresponding submission/transcription could not be found.",
        },
    )
    def get(self, request: Request, url: str) -> Response:
        """Find the submission/transcription corresponding to the URL."""
        normalized_url = normalize_url(url)
        if normalized_url is None:
            return Response(data="Invalid URL.", status=status.HTTP_400_BAD_REQUEST,)

        data = find_by_url(normalized_url)
        if data is None:
            return Response(
                data="No submission or transcription found for the given URL.",
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(data=data, status=status.HTTP_200_OK)
