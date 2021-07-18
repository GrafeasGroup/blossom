from typing import Any, Dict, Union

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import HttpResponseRedirect, redirect, render, reverse
from django.views.generic import DetailView, TemplateView, UpdateView, View

from api.models import Transcription
from utils.mixins import CSRFExemptMixin, GrafeasStaffRequired
from website.forms import AddUserForm, PostAddForm
from website.helpers import get_additional_context
from website.models import Post


def index(request: HttpRequest) -> HttpResponse:
    """Build and render the homepage for the website."""
    context = {
        "posts": Post.objects.filter(
            published=True,
            standalone_section=False,
            show_in_news_view=True,
            engineeringblogpost=False,
        ).order_by("-date")
    }
    context = get_additional_context(context)
    return render(request, "website/index.html", context)


class PostDetail(DetailView):
    """Render a specific post on the website."""

    model = Post
    template_name = "website/post_detail.html"

    def get_context_data(self, **kwargs: object) -> Dict:
        """Build the context dict with extra data needed for the templates."""
        context = super().get_context_data(**kwargs)
        context = get_additional_context(context)
        return context


def post_view_redirect(request: HttpRequest, pk: int, slug: str) -> HttpResponse:
    """Compatibility layer to take in old-style PK+slug urls and return slug only."""
    return HttpResponseRedirect(reverse("post_detail", kwargs={"slug": slug}))


class PostUpdate(GrafeasStaffRequired, UpdateView):
    """Modify a post on the website."""

    model = Post
    fields = [
        "title",
        "body",
        "published",
        "standalone_section",
        "header_order",
        "engineeringblogpost",
    ]
    template_name = "website/generic_form.html"

    def get_context_data(self, **kwargs: object) -> Dict:
        """Build the context dict with extra data needed for the templates."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "enable_trumbowyg": True,
                # id of html element we want to convert
                "trumbowyg_target": "id_body",
                "fullwidth_view": True,
            }
        )
        context = get_additional_context(context)
        return context


class PostAdd(GrafeasStaffRequired, TemplateView):
    def get(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        """
        Build and render the page for adding a new post.

        This applies to both main site and the engineering blog.
        """
        context = {
            "form": PostAddForm(),
            "header": "Add a new post!",
            "subheader": (
                'Remember to toggle "Published" if you want your post to appear!'
            ),
            # enable the WYSIWYG editor
            "enable_trumbowyg": True,
            # id of html element we want to attach the trumbowyg to
            "trumbowyg_target": "id_body",
            "fullwidth_view": True,
        }
        context = get_additional_context(context)
        return render(request, "website/generic_form.html", context)

    def post(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        """Save a new blog post when a POST request is sent to the server."""
        form = PostAddForm(request.POST)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.author = request.user
            new_post.save()
            return HttpResponseRedirect(f"{new_post.get_absolute_url()}edit")


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

    def get_preapproved_transcription(self) -> Union[Transcription, None]:
        """Return a specific transcription for use."""
        PREAPPROVED = [
            15372,  # image description
            15373,  # text messages
            101816,  # youtube comment
            21400,  # twitter
            20085,  # image of text
            102619,  # twitter
        ]
        # TODO: actually write this logic instead of making the linter happy
        PREAPPROVED[0]

    def get(self, request: HttpRequest) -> HttpResponse:
        """Choose appropriate practice page and render it."""
        context = get_additional_context()

        # if transcription_id := request.GET.get('transcription_id'):
        #     # convert the page to the version with the text fields
        #     transcription = get_object_or_404(Transcription, id=transcription_id)
        #     context.update(
        #         {
        #             'transcription': transcription,
        #             'source_url': transcription.submission.content_url
        #         }
        #     )

        return render(request, "website/practice.html", context)

    def post(self, request: HttpRequest) -> None:
        """Post things."""
        ...


class AdminView(GrafeasStaffRequired, TemplateView):
    def get(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        """Render the admin view."""
        context = {"posts": Post.objects.all()}
        context = get_additional_context(context)
        return render(request, "website/admin.html", context)


# superadmin role
@staff_member_required
def user_create(request: HttpRequest) -> HttpResponse:
    """Render the user creation view."""
    if request.method == "POST":
        form = AddUserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("homepage")

    else:
        form = AddUserForm()

    context = {"form": form, "header": "Create New User"}

    return render(request, "website/generic_form.html", context)


def handler404(request: HttpRequest, exception: Any) -> HttpResponse:
    """View to handle 404 errors."""
    context = get_additional_context(
        {
            "error_message": (
                "Hm... that page doesn't seem to exist. Try a different link?"
            )
        }
    )
    return render(request, "website/error.html", context)


def handler500(request: HttpRequest) -> HttpResponse:
    """View to handle 500 errors."""
    context = get_additional_context(
        {
            "error_message": (
                "Something went wrong and the site broke. Try your action again?"
            )
        }
    )
    return render(request, "website/error.html", context)
