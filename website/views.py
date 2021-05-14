from typing import Dict

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import HttpResponseRedirect, redirect, render
from django.views.generic import DetailView, TemplateView, UpdateView

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


class LoginView(TemplateView):
    def get(self, request, *args, **kwargs):
        form = LoginForm()
        return render(request, "website/generic_form.html", {"form": form})

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if user := EmailBackend().authenticate(
                username=data.get("email"), password=data.get("password")
            ):
                login(request, user)
                return HttpResponseRedirect(request.GET.get("next", "/"))
            return HttpResponseRedirect("/")


def LogoutView(request):
    logout(request)
    return HttpResponseRedirect("/")


class PostView(TemplateView):
    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass


class PostDetail(DetailView):
    """Render a specific post on the website."""

    model = Post
    query_pk_and_slug = True
    template_name = "website/post_detail.html"

    def get_context_data(self, **kwargs: object) -> Dict:
        """Build the context dict with extra data needed for the templates."""
        context = super().get_context_data(**kwargs)
        context = get_additional_context(context)
        return context


class PostUpdate(LoginRequiredMixin, UpdateView):
    """Modify a post on the website."""

    model = Post
    query_pk_and_slug = True
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
            }
        )
        context = get_additional_context(context)
        return context


class PostAdd(LoginRequiredMixin, TemplateView):
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


class AdminView(LoginRequiredMixin, TemplateView):
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
