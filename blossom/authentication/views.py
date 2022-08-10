from django.contrib.auth import login, logout
from django.http.response import HttpResponse
from django.shortcuts import HttpResponseRedirect, render, reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from rest_framework.request import Request

from blossom.authentication.backends import EmailBackend
from blossom.website.forms import LoginForm
from blossom.website.helpers import get_additional_context


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(TemplateView):
    def get(self, request: Request, *args: object, **kwargs: object) -> HttpResponse:
        """Retrieve the rendered login form."""
        form = LoginForm()
        context = get_additional_context({"form": form, "slim_form": True})
        if next_path := request.GET.get("next", None):
            context.update({"next": next_path})
        return render(request, "website/generic_form.html", context)

    def post(
        self, request: Request, *args: object, **kwargs: object
    ) -> HttpResponseRedirect:
        """Post the response to the login form."""
        form = LoginForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if user := EmailBackend().authenticate(
                username=data.get("email"), password=data.get("password")
            ):
                login(request, user)

                if request.GET.get("next", None):
                    location = request.GET.get("next")
                else:
                    location = "/"

                return HttpResponseRedirect(location)
            return HttpResponseRedirect(request.build_absolute_uri())


def logout_view(request: Request) -> HttpResponseRedirect:
    """Log out the user who has sent the request."""
    logout(request)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("homepage")))
