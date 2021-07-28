import random

from django.http import HttpRequest, HttpResponse, HttpResponseServerError
from django.shortcuts import get_object_or_404, render
from django.views.generic import View

from api.models import Transcription
from utils.mixins import CSRFExemptMixin
from website.helpers import get_additional_context


class PracticeTranscription(CSRFExemptMixin, View):
    """
    A page to practice writing transcriptions.

    This view consists of three pages:
    * the welcome page where you can set how long of a transcription that
        you want to attempt
    * the writing page with the content to transcribe
    * the original transcription so that folks can look at the differences

    QSP:
    &transcription_id -- the source transcription with practice page
    &new -- get a new transcription and re-render page

    Example urls:
    * GET /practice/ -> welcome page
    * GET /practice/?transcription_id=4 -> practice page
    * POST /practice/?transcription_id=4 -> show attempt and original
    """

    PREAPPROVED = [
        15372,  # image description
        15373,  # text messages
        101816,  # youtube comment
        21400,  # twitter
        20085,  # image of text
        102619,  # twitter
        102773,  # code
        15021,  # large sign
    ]

    def get_preapproved_transcription(self) -> Transcription:
        """Return a specific transcription for use."""
        return Transcription.objects.get(id=random.choice(self.PREAPPROVED))

    def get(self, request: HttpRequest) -> HttpResponse:
        """Choose appropriate practice page and render it."""
        context = get_additional_context({"fullwidth_view": True})

        if transcription_id := request.GET.get("transcription_id"):
            transcription_id = int(transcription_id)
            if transcription_id not in self.PREAPPROVED:
                raise HttpResponseServerError

            # convert the page to the version with the text fields
            transcription = get_object_or_404(Transcription, id=transcription_id)
            context.update(
                {
                    "transcription": transcription,
                    "source_url": transcription.submission.content_url,
                }
            )

        return render(request, "app/index.html", context)

    def post(self, request: HttpRequest) -> None:
        """Post things."""
        # transcription = get_object_or_404(Transcription, id=transcription_id)
        # context.update(
        #     {
        #         'transcription': transcription,
        #         'source_url': transcription.submission.content_url
        #     }
        # )
        ...
