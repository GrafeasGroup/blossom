from blossom.authentication.backends import EmailBackend
from blossom.website.forms import LoginForm
from django.contrib.auth import login, logout
from django.shortcuts import render, HttpResponseRedirect
from django.urls import resolve
from django.urls.exceptions import Resolver404, NoReverseMatch
from django.urls.resolvers import get_resolver
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django_hosts.resolvers import get_host_patterns, reverse


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(TemplateView):
    def get_redirect(self, request, hosts):
        # work around a super obnoxious problem with django-hosts where if it
        # doesn't find the url that you're looking for in the default host,
        # it just gives up. This will allow us to cycle through the hosts and
        # try to find one that returns a ResolverMatch.

        # first let's see if the requested url DOES resolve in the base host.
        nextpath = request.GET["next"]

        if nextpath.startswith("http"):
            nextpath = nextpath[nextpath.index("//") :]

        try:
            match = resolve(nextpath)
            return reverse(match.view_name)
        except Resolver404:
            pass

        for h in hosts:
            try:
                match = get_resolver(h.urlconf).resolve(nextpath)
                try:
                    return reverse(match.view_name, host=match.namespace)
                except NoReverseMatch:
                    continue
            except Resolver404:
                continue

        # still haven't found a match? The only thing left is that it's really
        # borked or it's a full url to something like the wiki.
        if nextpath.endswith(request.get_host()) or nextpath.endswith(
            request.get_host() + "/"
        ):
            return nextpath

        raise Resolver404

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

                if request.GET.get("next", None):
                    hosts = get_host_patterns()
                    location = self.get_redirect(request, hosts)
                else:
                    location = "/"

                return HttpResponseRedirect(location)
            return HttpResponseRedirect(request.build_absolute_uri())


def LogoutView(request):
    logout(request)
    return HttpResponseRedirect("/")
