from typing import Optional, TypedDict
from urllib.parse import urlparse

from django.views.decorators.csrf import csrf_exempt
from drf_yasg.openapi import Parameter
from drf_yasg.openapi import Response as DocResponse
from drf_yasg.openapi import Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from blossom.api.models import Submission, Transcription
from blossom.api.serializers import FindResponseSerializer
from blossom.authentication.models import BlossomUser


class FindResponse(TypedDict):
    submission: Submission
    author: Optional[BlossomUser]
    transcription: Optional[Transcription]
    ocr: Optional[Transcription]


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
    submissions = Submission.objects.filter(**{f"{url_type}__istartswith": url})
    if submissions.count() == 0:
        return None

    # Get submission
    submission = submissions[0]
    # Get author
    author = submission.claimed_by
    # Get transcription
    if author is not None:
        transcriptions = submission.transcription_set.filter(author=author)
        transcription = transcriptions[0] if transcriptions.count() > 0 else None
    else:
        transcription = None
    # Get OCR
    ocr_transcriptions = submission.transcription_set.filter(author__is_bot=True)
    ocr = ocr_transcriptions[0] if ocr_transcriptions.count() > 0 else None

    return {
        "submission": submission,
        "author": author,
        "transcription": transcription,
        "ocr": ocr,
    }


def extract_core_url(url: str) -> str:
    """Extract the minimal unique part of the URL.

    https://reddit.com/r/TranscribersOfReddit/comments/plmx5n/curatedtumblr_image_im_an_atheist_but_yall_need/
    will be converted to
    https://reddit.com/r/TranscribersOfReddit/comments/plmx5n

    This way we can handle submissions and comments uniformly.
    """
    url_parts = url.split("/")
    return "/".join(url_parts[:7])


def find_by_url(url: str) -> Optional[FindResponse]:
    """Find the objects by a normalized URL.

    Example URL:
    https://reddit.com/r/TranscribersOfReddit/comments/plmx5n/curatedtumblr_image_im_an_atheist_but_yall_need/
    """
    url_parts = url.split("/")

    if "reddit" not in url or len(url_parts) < 5:
        return None

    subreddit = url_parts[4]
    core_url = extract_core_url(url)

    if subreddit.casefold() == "transcribersofreddit":
        # Find the submission on ToR
        return find_by_submission_url(core_url, "tor_url")
    else:
        # Find the submission on the partner sub
        return find_by_submission_url(core_url, "url")


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
                required=True,
            ),
        ],
        required=["url"],
        responses={
            200: DocResponse(
                "The URL has been found!",
                schema=Schema(
                    type="object",
                    # TODO: Use the schemas of the corresponding models
                    properties={
                        "submission": Schema(type="object"),
                        "author": Schema(type="object"),
                        "transcription": Schema(type="object"),
                        "ocr": Schema(type="object"),
                    },
                ),
            ),
            400: "The given URL has an invalid format.",
            404: "The corresponding submission/transcription could not be found.",
        },
    )
    def get(self, request: Request) -> Response:
        """Find the submission/transcription corresponding to the URL."""
        url = request.query_params.get("url")
        normalized_url = normalize_url(url)
        if normalized_url is None:
            return Response(
                data="Invalid URL.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = find_by_url(normalized_url)
        if data is None:
            return Response(
                data="No submission or transcription found for the given URL.",
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            data=FindResponseSerializer(data, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
