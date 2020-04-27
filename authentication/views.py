from typing import List

from django.contrib.auth import login, logout
from django.http.response import HttpResponse
from django.shortcuts import HttpResponseRedirect, render
from django.urls import resolve
from django.urls.exceptions import NoReverseMatch, Resolver404
from django.urls.resolvers import get_resolver
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django_hosts import host
from django_hosts.resolvers import get_host_patterns, reverse
from rest_framework.request import Request

from authentication.backends import EmailBackend
from website.forms import LoginForm


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(TemplateView):
    @staticmethod
    def get_redirect(request: Request, hosts: List[host]) -> str:
        """
        Get redirect URL from the available hosts.

        This method is used to work around the problem with django-hosts, where
        it only looks for the URLs in the default host rather than in all
        available hosts. This method first checks whether the base host can
        resolve the request next. If this is not the case, the other hosts are
        checked in similar fashion.

        :param request: the HTTP request
        :param hosts: the available Django Hosts
        :returns: the URL to where the request should be redirected
        :raise Resolver404: if the URL cannot be resolved in any available host
        """
        next_path = f'//{request.GET["next"].split("//")[-1]}'
        try:
            # Check whether the requested URL DOES resolve in the base host.
            match = resolve(next_path)
            return reverse(match.view_name)
        except Resolver404:
            # If this is not the case, check whether it resolves in another host.
            for host_instance in hosts:
                try:
                    match = get_resolver(host_instance.urlconf).resolve(next_path)
                    return reverse(match.view_name, host=match.namespace)
                except (NoReverseMatch, Resolver404):
                    continue

        # If no match is found, either it's a full URL or the redirect cannot be made.
        request_host = request.get_host()
        if next_path.endswith((request_host, f"{request_host}/")):
            return next_path
        else:
            raise Resolver404

    def get(self, request: Request, *args: object, **kwargs: object) -> HttpResponse:
        """Retrieve the rendered login form."""
        form = LoginForm()
        return render(request, "website/generic_form.html", {"form": form})

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
                    hosts = get_host_patterns()
                    location = self.get_redirect(request, hosts)
                else:
                    location = "/"

                return HttpResponseRedirect(location)
            return HttpResponseRedirect(request.build_absolute_uri())


def logout_view(request: Request) -> HttpResponseRedirect:
    """Log out the user who has sent the request."""
    logout(request)
    return HttpResponseRedirect("/")
