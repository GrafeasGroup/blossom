import json
import logging
import pathlib
import random
import uuid
from datetime import timedelta

import markdown
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import Length
from django.http import HttpRequest, HttpResponse
from django.shortcuts import (
    HttpResponseRedirect,
    get_object_or_404,
    redirect,
    render,
    reverse,
)
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from rest_framework import status

from blossom.api.models import Source, Submission, Transcription
from blossom.api.slack.actions import ask_about_removing_post
from blossom.api.views.submission import SubmissionViewSet
from blossom.app.permissions import RequireCoCMixin, require_coc, require_reddit_auth
from blossom.app.reddit_actions import (
    Flair,
    advertise,
    edit_transcription,
    flair_post,
    submit_transcription,
)
from blossom.app.validation import (
    check_for_fenced_code_block,
    check_for_formatting_issues,
    check_for_unescaped_subreddit,
    check_for_unescaped_username,
    clean_fenced_code_block,
)
from blossom.ocr.helpers import escape_reddit_links, replace_shortlinks
from blossom.utils.mixins import CSRFExemptMixin
from blossom.utils.requests import convert_to_drf_request
from blossom.website.helpers import get_additional_context

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
    "*Image Transcription:{content_type}*\n\n---\n\n{transcription}\n\n---\n\n"
    "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;and&#32;"
    "you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;like&#32;more&#32;"
    "information&#32;on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;we&#32;do&#32;"
    "it,&#32;click&#32;here!](https://www.reddit.com/r/TranscribersOfReddit/wiki/index)"
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
def view_previous_transcriptions(request: HttpRequest) -> HttpResponse:
    """Show the user their latest transcriptions so that they can edit them if needed."""
    transcriptions = (
        Transcription.objects.annotate(original_id_len=Length("original_id"))
        .filter(
            author=request.user, original_id_len__lt=14, submission__title__isnull=False
        )
        .order_by("-create_time")[:25]
    )
    context = get_additional_context(
        {"transcriptions": transcriptions, "fullwidth_view": True}
    )
    return render(request, "app/view_transcriptions.html", context)


@login_required
@require_coc
@require_reddit_auth
def choose_transcription(request: HttpRequest) -> HttpResponse:
    """Provide a user with transcriptions to choose from."""
    time_delay = timezone.now() - timedelta(
        hours=settings.OVERRIDE_ARCHIVIST_DELAY_TIME
        if settings.OVERRIDE_ARCHIVIST_DELAY_TIME
        else settings.ARCHIVIST_DELAY_TIME
    )
    submissions = Submission.objects.annotate(
        original_id_len=Length("original_id")
    ).filter(
        original_id_len__lt=10,
        completed_by=None,
        claimed_by=None,
        create_time__gte=time_delay,
        removed_from_queue=False,
        archived=False,
    )

    options_list = [obj for obj in submissions if obj.is_image]

    if len(options_list) > 3:
        # we have more to choose from, so let's grab 3
        temp = []
        for _ in range(3):
            submission = random.choice(options_list)
            temp.append(options_list.pop(options_list.index(submission)))
        options = temp
    else:
        options = options_list

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

    if len(options) == 0:
        completed_post_count = (
            Submission.objects.annotate(original_id_len=Length("original_id"))
            .filter(
                original_id_len__lt=10,
                completed_by__isnull=False,
                create_time__gte=time_delay,
            )
            .count()
        )
        if completed_post_count == 0:
            # if it's not zero, then we cleared the queue and will show that page instead.
            context.update({"show_error_page": True})
    claimed_submissions = Submission.objects.filter(
        claimed_by=request.user, archived=False, completed_by__isnull=True
    )
    context.update({"claimed_submissions": claimed_submissions})

    if request.user.ranked_up:
        ending = random.choice(EXCITEMENT)
        messages.success(request, f"You ranked up to {request.user.get_rank}! {ending}")
        context.update({"show_confetti": True})

    return render(request, "app/choose_transcription.html", context)


def get_and_format_templates() -> list:
    """Load all templates and format them appropriately."""
    md = markdown.Markdown(output_format="html")
    with open(
        pathlib.Path(__file__).parent / "transcription_templates.json", "r"
    ) as file:
        data = json.load(file)
        for template in data.keys():
            if notes := data[template].get("notes"):
                data[template]["notes"] = [md.convert(note) for note in notes]
    return data


def update_context_with_proxy_data(submission: Submission, context: dict) -> dict:
    """Verify that if proxy data is needed, it is formatted and added to the context."""
    if "i.redd.it" in submission.content_url:
        # just grab the `abcde.jpg` bit out of the url so that we can route it
        # through the proxy for OpenSeaDragon
        context.update({"ireddit_content_url": submission.content_url.split("/")[-1]})
    elif "imgur.com" in submission.content_url:
        imgur_content_url = submission.content_url.split("/")[-1]
        # Check if the URL links to the imgur post instead of directly to the image
        # Kinda dirty, but this way we can account for all image formats
        if "." not in imgur_content_url:
            imgur_content_url += ".jpg"

        context.update({"imgur_content_url": imgur_content_url})
    return context


def update_context_with_session_data(request: HttpRequest, context: dict) -> dict:
    """Pull data off the request session if present and add to context."""
    if transcription := request.session.get("transcription"):
        context.update({"transcription": transcription})

    if heading := request.session.get("heading"):
        context.update({"heading": heading})

    if issues := request.session.get("issues"):
        context.update(
            {"issues": [f"app/partials/errors/{issue}.partial" for issue in issues]}
        )
    return context


def remove_old_session_data(request: HttpRequest) -> None:
    """Remove old session data from the request."""
    del request.session["transcription"]
    del request.session["heading"]
    del request.session["issues"]
    del request.session["submission_id"]


def get_and_clean_content_type(request: HttpRequest) -> [str, None]:
    """Retrieve and format the content type if present."""
    content_type = request.POST.get("transcription_type")
    if content_type:
        # add in the space before the type so that it renders correctly
        content_type = " " + content_type.strip()
    return content_type


def add_transcription_data_to_session_and_redirect(
    request: HttpRequest, transcription: str, submission_id: str, issues: list
) -> HttpResponse:
    """Stash the important stuff in the session so that we can GET it back."""
    # we need this information to be accessible on the GET call that comes after
    # the failed POST, so we'll stuff everything necessary into the session.

    # escape the backticks so that they can be rendered properly by the JS
    # template literals in the html template
    request.session["transcription"] = transcription.replace("`", r"\`")
    request.session["heading"] = request.POST.get("transcription_type")
    request.session["issues"] = list(issues) if issues else ["no_transcription_found"]
    # store this one too so that we know which submission this information is for
    request.session["submission_id"] = submission_id
    return redirect("transcribe_submission", submission_id=submission_id)


class EditSubmissionTranscription(
    CSRFExemptMixin, LoginRequiredMixin, RequireCoCMixin, View
):
    def get(self, request: HttpRequest, submission_id: int) -> HttpResponse:
        """Render the transcription view with data from an existing transcription."""
        submission = get_object_or_404(Submission, id=submission_id)
        transcription = submission.transcription_set.filter(author=request.user).first()

        if not transcription:
            messages.error(
                request,
                f"Cannot find transcription for submission {submission.id} by you!",
            )
            return redirect("choose_transcription")

        context = get_additional_context({"fullwidth_view": True})
        context.update({"submission": submission})
        context.update({"transcription_templates": get_and_format_templates()})
        context.update({"edit_mode": True})
        context = update_context_with_proxy_data(submission, context)

        if s_id := request.session.get("submission_id"):
            if s_id == submission_id:
                # it's for the submission we're currently working on.
                context = update_context_with_session_data(request, context)
            else:
                # it's old data. Nuke it.
                remove_old_session_data(request)

        # if this is a submission we're revisiting because of an error, this value
        # won't get nuked in the previous step. If this is something new, then it
        # won't be here.
        if not request.session.get("submission_id"):
            text = transcription.text
            context.update(
                {
                    "transcription": text[
                        text.index("---") + 5 : text.rindex("---") - 2
                    ].replace("`", r"\`")
                }
            )
            context.update(
                {"heading": text[text.index(":") + 1 : text.index("---") - 3].strip()}
            )

        return render(request, "app/transcribing.html", context)

    def post(self, request: HttpRequest, submission_id: int) -> HttpResponse:
        """Handle a resubmitted transcription."""
        submission_obj: Submission = Submission.objects.get(id=submission_id)
        transcription_obj: Transcription = submission_obj.transcription_set.filter(
            author=request.user
        ).first()

        transcription: str = request.POST.get("transcription")
        transcription = transcription.replace("\r\n", "\n")

        issues = check_for_formatting_issues(transcription)
        if len(issues) > 0 or not transcription:
            return add_transcription_data_to_session_and_redirect(
                request, transcription, submission_id, issues
            )
        else:
            # we're good to go -- let's submit it!
            if check_for_fenced_code_block(transcription):
                transcription = clean_fenced_code_block(transcription)

            if check_for_unescaped_subreddit(
                transcription
            ) or check_for_unescaped_username(transcription):
                transcription = escape_reddit_links(transcription)
            transcription = replace_shortlinks(transcription)

            content_type = get_and_clean_content_type(request)

            transcription_obj.text = TRANSCRIPTION_TEMPLATE.format(
                content_type=content_type,
                transcription=transcription,
            )
            transcription_obj.save()
            edit_transcription(request, transcription_obj, submission_obj)
            messages.success(request, "Looks good -- all edited!")
            return redirect("choose_transcription")


class TranscribeSubmission(CSRFExemptMixin, LoginRequiredMixin, RequireCoCMixin, View):
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
        context.update({"edit_mode": False})

        context.update({"transcription_templates": get_and_format_templates()})

        context = update_context_with_proxy_data(submission, context)

        # if they posted a bad transcription and we want them to fix it, grab
        # the stored values and add them to the current context, then delete them
        # from the session so they don't get accidentally shown twice.
        if s_id := request.session.get("submission_id"):
            if s_id == submission_id:
                # it's for the submission we're currently working on.
                context = update_context_with_session_data(request, context)
            else:
                # it's old data. Nuke it.
                remove_old_session_data(request)

        return render(request, "app/transcribing.html", context)

    def post(self, request: HttpRequest, submission_id: int) -> HttpResponse:
        """Handle a submitted transcription."""
        transcription: str = request.POST.get("transcription")
        transcription = transcription.replace("\r\n", "\n")

        issues = check_for_formatting_issues(transcription)
        if len(issues) > 0 or not transcription:
            return add_transcription_data_to_session_and_redirect(
                request, transcription, submission_id, issues
            )
        else:
            # we're good to go -- let's submit it!
            if check_for_fenced_code_block(transcription):
                transcription = clean_fenced_code_block(transcription)

            if check_for_unescaped_subreddit(
                transcription
            ) or check_for_unescaped_username(transcription):
                transcription = escape_reddit_links(transcription)
            transcription = replace_shortlinks(transcription)

            content_type = get_and_clean_content_type(request)

            text = TRANSCRIPTION_TEMPLATE.format(
                content_type=content_type,
                transcription=transcription,
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
        return redirect("choose_transcription")
    submission_obj = Submission.objects.get(id=submission_id)

    if request.GET.get("reason") is not None:
        # There's a reason they're reporting this, so we should remove it from the queue
        # until it can be reviewed. We guard here because an unclaim without a reason
        # is just returning the post back to the queue to get something else.
        submission_obj.removed_from_queue = True
        submission_obj.save(skip_extras=True)
        ask_about_removing_post(request, submission_obj)

    flair_post(submission_obj, Flair.unclaimed)
    return redirect("choose_transcription")


@login_required
@require_coc
def report_submission(request: HttpRequest, submission_id: int) -> HttpResponseRedirect:
    """Process reports without unclaiming that originate from the web app side."""
    reason = request.GET.get("reason")
    submission_obj = Submission.objects.get(id=submission_id)

    # Reports that come in here are always for a specific reason, so remove the post
    # from the queue until we can investigate.
    submission_obj.removed_from_queue = True
    submission_obj.report_reason = reason
    submission_obj.save(skip_extras=True)

    ask_about_removing_post(submission_obj, reason)

    log.info(f"Sending message to Slack to ask about removing {submission_id}")
    return redirect("choose_transcription")
