import random
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models.functions import Length
from django.http import HttpRequest, HttpResponse, HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from api.models import Submission, Transcription
from app.permissions import require_coc, require_reddit_auth
from utils.mixins import CSRFExemptMixin
from website.helpers import get_additional_context


@login_required
@csrf_exempt
def accept_coc(request: HttpRequest) -> HttpResponse:
    """Show the Code of Conduct and ask the volunteer to accept it."""
    if request.method == "POST":
        request.user.accepted_coc = True
        request.user.save()
        return redirect(reverse("choose_transcription") + "?show_tutorial=1")
    else:
        return render(request, "app/accept_coc.html", get_additional_context())


@login_required
@require_coc
@require_reddit_auth
def choose_transcription(request: HttpRequest) -> HttpResponse:
    """Provide a user with transcriptions to choose from."""
    # time_delay = timezone.now() - timedelta(hours=settings.ARCHIVIST_DELAY_TIME)
    time_delay = timezone.now() - timedelta(hours=60)
    options = Submission.objects.annotate(original_id_len=Length("original_id")).filter(
        original_id_len__lt=10,
        completed_by=None,
        claimed_by=None,
        create_time__gte=time_delay,
    )

    if options.count() > 3:
        # we have more to choose from, so let's grab 3
        temp = []
        while len(temp) < 3:
            submission = random.choice(options)
            # todo: we want to eventually handle other types of content here, but
            #  we simply aren't ready for it yet.
            if submission not in temp and submission.is_image:
                temp.append(submission)
        options = temp

    for submission in options:
        # todo: add check for source. This will need to happen after we convert
        #  sources to the individual subreddits
        if not submission.title:
            # we have a lot of submissions that don't have a title, but we
            # need it for this next page. Just grab the title and save it.
            post = request.user.reddit.submission(url=submission.url)
            submission.title = post.title
            submission.nsfw = post.over_18
            submission.save(skip_extras=True)

    context = get_additional_context({"options": options, "fullwidth_view": True})

    # messages.success(request, "You ranked up to Jade! Congrats!!")
    # context.update({"show_confetti": True})
    return render(request, "app/choose_transcription.html", context,)


class TranscribeSubmission(View):
    def get(self, request: HttpRequest, submission_id: int) -> HttpResponse:
        """Provide the transcription view."""
        context = get_additional_context({"fullwidth_view": True})
        submission = get_object_or_404(Submission, id=submission_id)
        context.update({"submission": submission})

    def post(self, request: HttpRequest, submission_id: int) -> HttpResponse:
        """Handle a submitted transcription."""
        ...


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
