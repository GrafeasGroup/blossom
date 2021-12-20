import json
import logging
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
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from rest_framework import status

from api.models import Source, Submission, Transcription
from api.views.slack_helpers import client
from api.views.submission import SubmissionViewSet
from app.permissions import require_coc, require_reddit_auth
from app.reddit_actions import Flair, advertise, flair_post, submit_transcription
from app.validation import (
    check_for_fenced_code_block,
    check_for_formatting_issues,
    check_for_unescaped_subreddit,
    check_for_unescaped_username,
    clean_fenced_code_block,
)
from ocr.helpers import escape_reddit_links, replace_shortlinks
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
    "Image Transcription: {content_type}\n\n---\n\n{transcription}\n\n---\n\n"
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
    time_delay = timezone.now() - timedelta(hours=settings.ARCHIVIST_DELAY_TIME)
    # todo: remove this when finished testing raw functionality
    # time_delay = timezone.now() - timedelta(hours=330)
    options = Submission.objects.annotate(original_id_len=Length("original_id")).filter(
        original_id_len__lt=10,
        completed_by=None,
        claimed_by=None,
        create_time__gte=time_delay,
        removed_from_queue=False,
        archived=False,
    )

    if options.count() > 3:
        # we have more to choose from, so let's grab 3
        temp = []
        options_list = list(options)
        for _ in range(options.count()):
            if len(temp) >= 3:
                break
            # What if the only options we have here are video options? This will
            # terminate when it runs out of options to try but we at least get
            # to inject a little randomness into it.
            submission = random.choice(options_list)
            # todo: we want to eventually handle other types of content here, but
            #  we simply aren't ready for it yet.
            if submission.is_image:
                temp.append(options_list.pop(options_list.index(submission)))

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
        if len(issues) > 0 or not transcription:
            #            # stash the important stuff in the session so that we can
            # retrieve it on the other side

            # escape the backticks so that they can be rendered properly by the JS
            # template literals in the html template
            request.session["transcription"] = transcription.replace(
                "`", r"\`"  # noqa: W605
            )
            request.session["heading"] = request.POST.get("transcription_type")
            request.session["issues"] = (
                list(issues) if issues else ["no_transcription_found"]
            )
            # store this one too so that we know which submission this information is for
            request.session["submission_id"] = submission_id
            return redirect("transcribe_submission", submission_id=submission_id)
        else:
            # we're good to go -- let's submit it!
            if check_for_fenced_code_block(transcription):
                transcription = clean_fenced_code_block(transcription)

            if check_for_unescaped_subreddit(
                transcription
            ) or check_for_unescaped_username(transcription):
                transcription = escape_reddit_links(transcription)
            transcription = replace_shortlinks(transcription)

            text = TRANSCRIPTION_TEMPLATE.format(
                content_type=request.POST.get("transcription_type"),
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


@send_to_worker
def ask_about_removing_post(request: HttpRequest, submission: Submission) -> None:
    """Ask Slack if we want to remove a reported submission or not."""
    # created using the Slack Block Kit Builder https://app.slack.com/block-kit-builder/
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "This submission was reported -- please investigate and decide"
                    " whether it should be removed."
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ("Submission: <{url}|{title}>\nReport reason: {reason}"),
            },
        },
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Keep"},
                    "value": "keep_submission_{}",
                },
                {
                    "type": "button",
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Remove",},  # noqa: E231
                    "value": "remove_submission_{}",
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Are you sure?"},
                        "text": {
                            "type": "mrkdwn",
                            "text": "This will remove the submission from the queue.",
                        },
                        "confirm": {"type": "plain_text", "text": "Nuke it"},
                        "deny": {"type": "plain_text", "text": "Back"},
                    },
                },
            ],
        },
    ]

    blocks[2]["text"]["text"] = blocks[2]["text"]["text"].format(
        url=submission.url, title=submission.title, reason=request.GET.get("reason")
    )

    blocks[-1]["elements"][0]["value"] = blocks[-1]["elements"][0]["value"].format(
        submission.id
    )
    blocks[-1]["elements"][1]["value"] = blocks[-1]["elements"][1]["value"].format(
        submission.id
    )

    client.chat_postMessage(channel="removed_posts", blocks=blocks)


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

    flair_post(Submission.objects.get(id=submission_id), Flair.unclaimed)
    ask_about_removing_post(request, submission_id)
    return redirect("choose_transcription")
