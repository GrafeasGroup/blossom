import json
import logging
import random
import uuid
from datetime import timedelta

import markdown
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import Length
from django.http import HttpRequest, HttpResponse, HttpResponseServerError
from django.shortcuts import (
    HttpResponseRedirect,
    get_object_or_404,
    redirect,
    render,
    reverse,
)
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from rest_framework import status

from api.models import Source, Submission, Transcription
from api.views.submission import SubmissionViewSet
from app.permissions import require_coc, require_reddit_auth
from app.reddit_actions import Flair, advertise, flair_post, submit_transcription
from app.validation import (
    check_for_fenced_code_block,
    check_for_formatting_issues,
    clean_fenced_code_block,
)
from utils.mixins import CSRFExemptMixin
from utils.requests import convert_to_drf_request
from utils.workers import send_to_worker
from website.helpers import get_additional_context

log = logging.getLogger(__name__)

EXCITEMENT = [
    "Woohoo!",
    "Huzzah!",
    "Fantastic!",
    "Wonderful!",
    "Great job!",
    "Go you!",
    "Awesome!",
    "High five!",
    "Congrats!",
]

TRANSCRIPTION_TEMPLATE = (
    "Image Transcription: {0}\n\n---\n\n{1}\n\n---\n\n"
    "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;"
    "for&#32;Reddit&#32;and&#32;you&#32;could&#32;be&#32;too!&#32;"
    "[If&#32;you'd&#32;like&#32;more&#32;information&#32;on&#32;what&#32;"
    "we&#32;do&#32;and&#32;why&#32;we&#32;do&#32;it,&#32;click&#32;here!]"
    "(https://www.reddit.com/r/TranscribersOfReddit/wiki/index)"
)


def get_blossom_app_source() -> Source:
    """Get the source object for transcriptions completed using the App."""
    return Source.objects.get_or_create(name="TranscriptionApp")[0]


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
    time_delay = timezone.now() - timedelta(hours=130)
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

    claimed_submissions = Submission.objects.filter(
        claimed_by=request.user, archived=False, completed_by__isnull=True
    )
    context.update({"claimed_submissions": claimed_submissions})

    if request.user.ranked_up:
        ending = random.choice(EXCITEMENT)
        messages.success(request, f"You ranked up to {request.user.get_rank}! {ending}")
        context.update({"show_confetti": True})

    return render(request, "app/choose_transcription.html", context,)


@method_decorator(require_coc, name="dispatch")
class TranscribeSubmission(CSRFExemptMixin, LoginRequiredMixin, View):
    def get(  # noqa: C901
        self, request: HttpRequest, submission_id: int
    ) -> HttpResponse:
        """Provide the transcription view."""
        drf_request = convert_to_drf_request(
            request, data={"username": request.user.username}
        )
        viewset = SubmissionViewSet()
        # prepare the viewset for handling this request
        viewset.request = drf_request
        # I don't know why this isn't autopopulated, but if we don't set it here then
        # it explodes.
        viewset.format_kwarg = None
        response = viewset.claim(drf_request, submission_id)

        submission = get_object_or_404(Submission, id=submission_id)

        if response.status_code == status.HTTP_423_LOCKED:
            messages.error(
                request,
                "There is a problem with your account. Please contact the mods.",
            )
            return redirect("logout")

        if response.status_code == status.HTTP_409_CONFLICT:
            if submission.claimed_by != request.user:
                # only actually error if it's not claimed by us
                messages.error(
                    request,
                    "Sorry, that submission was claimed by someone else. Try grabbing a"
                    " different one!",
                )
                return redirect("choose_transcription")

        if response.status_code == 460:
            messages.error(
                request,
                "Sorry -- you need to complete the submissions already assigned to you"
                " before you take on more.",
            )
            return redirect("choose_transcription")

        flair_post(Submission.objects.get(id=submission_id), Flair.in_progress)

        context = get_additional_context({"fullwidth_view": True})
        context.update({"submission": submission})

        md = markdown.Markdown(output_format="html5")
        with open("app/transcription_templates.json", "r") as file:
            data = json.load(file)
            for template in data.keys():
                if notes := data[template].get("notes"):
                    data[template]["notes"] = [md.convert(note) for note in notes]

            context.update({"transcription_templates": data})

        if "i.redd.it" in submission.content_url:
            # just grab the `abcde.jpg` bit out of the url so that we can route it
            # through the proxy for OpenSeaDragon
            context.update(
                {"ireddit_content_url": submission.content_url.split("/")[-1]}
            )
        elif "imgur.com" in submission.content_url:
            context.update({"imgur_content_url": submission.content_url.split("/")[-1]})

        # if they posted a bad transcription and we want them to fix it, grab
        # the stored values and add them to the current context, then delete them
        # from the session so they don't get accidentally shown twice.
        if s_id := request.session.get("submission_id"):
            if s_id == submission_id:
                # it's for the submission we're currently working on.
                if transcription := request.session.get("transcription"):
                    context.update({"transcription": transcription})

                if heading := request.session.get("heading"):
                    context.update({"heading": heading})

                if issues := request.session.get("issues"):
                    context.update(
                        {
                            "issues": [
                                f"app/partials/errors/{issue}.partial"
                                for issue in issues
                            ]
                        }
                    )
            else:
                # it's old data. Nuke it.
                del request.session["transcription"]
                del request.session["heading"]
                del request.session["issues"]
                del request.session["submission_id"]

        return render(request, "app/transcribing.html", context)

    def post(self, request: HttpRequest, submission_id: int) -> HttpResponse:
        """Handle a submitted transcription."""
        transcription: str = request.POST.get("transcription")
        transcription = transcription.replace("\r\n", "\n")

        issues = check_for_formatting_issues(transcription)
        if len(issues) > 0:
            # stash the important stuff in the session so that we can
            # retrieve it on the other side

            # escape the backticks so that they can be rendered properly by the JS
            # template literals in the html template
            request.session["transcription"] = transcription.replace(
                "`", "\`"  # noqa: W605
            )
            request.session["heading"] = request.POST.get("transcription_type")
            request.session["issues"] = list(issues)
            # store this one too so that we know which submission this information is for
            request.session["submission_id"] = submission_id
            return redirect("transcribe_submission", submission_id=submission_id)
        else:
            # we're good to go -- let's submit it!
            if check_for_fenced_code_block(transcription):
                transcription = clean_fenced_code_block(transcription)

            text = TRANSCRIPTION_TEMPLATE.format(
                request.POST.get("transcription_type"), transcription
            )

            submission_obj = Submission.objects.get(id=submission_id)
            # We'll try and edit some of the fields after posting -- if posting fails,
            # then this is the default set of options that we want to have.
            transcription_obj = Transcription.objects.create(
                original_id=uuid.uuid4(),
                submission=submission_obj,
                author=request.user,
                url=None,
                source=get_blossom_app_source(),
                text=text,
                removed_from_reddit=True,
            )

            drf_request = convert_to_drf_request(
                request, data={"username": request.user.username}
            )
            viewset = SubmissionViewSet()
            # prepare the viewset for handling this request
            viewset.request = drf_request
            # I don't know why this isn't autopopulated, but if we don't set it here then
            # it explodes.
            viewset.format_kwarg = None
            response = viewset.done(drf_request, submission_id)

            if response.status_code == status.HTTP_423_LOCKED:
                messages.error(
                    request,
                    "There is a problem with your account. Please contact the mods.",
                )
                return redirect("logout")

            if response.status_code == status.HTTP_409_CONFLICT:
                messages.error(
                    request,
                    "This is marked as having been completed by someone else. Sorry!",
                )
                return redirect("choose_transcription")

            flair_post(submission_obj, Flair.completed)
            submit_transcription(request, transcription_obj, submission_obj)
            advertise(submission_obj)

            messages.success(
                request, "Nice work! Thanks for helping make somebody's day better!"
            )

            return redirect("choose_transcription")


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

    # todo: add tumblr post
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


@send_to_worker
def ask_about_removing_post(request: HttpRequest, submission: Submission) -> None:
    """Ask Slack if we want to remove a reported submission or not."""
    # TODO: make this fire a block kit question to slack with the reported reason asking
    #  if we want to remove it or not. The response should set `removed_from_queue` and
    #  nuke the submission from the Reddit queue.
    ...


@login_required
@require_coc
def unclaim_submission(
    request: HttpRequest, submission_id: int
) -> HttpResponseRedirect:
    """Process unclaims that originate from the web app side."""
    drf_request = convert_to_drf_request(
        request, data={"username": request.user.username}
    )
    response = SubmissionViewSet().unclaim(drf_request, submission_id)

    if response.status_code == status.HTTP_423_LOCKED:
        messages.error(
            request, "There is a problem with your account. Please contact the mods."
        )
        return redirect("logout")

    if response.status_code == status.HTTP_406_NOT_ACCEPTABLE:
        messages.error(
            request,
            "Not sure how you got there, but that submission is being handled by someone"
            " else.",
        )
        return redirect("choose_transcription")

    if response.status_code == status.HTTP_409_CONFLICT:
        messages.error(
            request,
            "That submission is already completed, so you'll want to choose a different"
            " one.",
        )

    flair_post(Submission.objects.get(id=submission_id), Flair.unclaimed)
    ask_about_removing_post(request, submission_id)
    return redirect("choose_transcription")
