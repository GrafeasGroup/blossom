from functools import wraps
from typing import Any, Callable

from decorator_include import decorator_include
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import path

from blossom.authentication.views import LoginView
from blossom.website.views import user_create

admin.autodiscover()
admin.site.login = LoginView.as_view()

handler404 = "blossom.website.views.handler404"
handler500 = "blossom.website.views.handler500"


def force_domain(domain: [str, None]) -> Any:
    """Enforce the appropriate domain name for a given route."""

    def decorator(func: Callable) -> Any:
        """Enforce the appropriate domain name for a given route."""

        @wraps(func)
        def inner_func(request: HttpRequest, *args: list, **kwargs: dict) -> Any:
            if settings.DEBUG or request.get_host() == "testserver":
                # Patch the request with either the configured hostname for testing
                # or the host that's required for this route.
                request.get_host = (
                    lambda: settings.OVERRIDE_HOST if settings.OVERRIDE_HOST else domain
                )
                return func(request, *args, **kwargs)

            if not domain:
                # This is so that we can set the request manipulation when in debug mode
                # on routes that otherwise don't get forced one way or another.
                return func(request, *args, **kwargs)

            if request.get_host() != domain:
                # The request came in on the wrong domain, so issue a redirect for
                # the same route so they come in from the right site.
                return redirect(request.scheme + "://" + domain + request.path)
            # everything's groovy -- let's roll
            return func(request, *args, **kwargs)

        return inner_func

    return decorator


# domainless urls
urlpatterns = [
    path("superadmin/newuser", user_create, name="user_create"),
    path("superadmin/", admin.site.urls),
    path("", decorator_include(force_domain(None), "blossom.authentication.urls")),
    path("api/", decorator_include(force_domain(None), "blossom.api.urls")),
]

# grafeas urls
urlpatterns += [
    path(
        "payments/",
        decorator_include(force_domain("grafeas.org"), "blossom.payments.urls"),
    ),
    path(
        "engineering/",
        decorator_include(force_domain("grafeas.org"), "blossom.engineeringblog.urls"),
    ),
    path("", decorator_include(force_domain("grafeas.org"), "blossom.website.urls")),
]

# thetranscription.app urls
if settings.ENABLE_APP:
    urlpatterns += [
        path(
            "app/",
            decorator_include(force_domain("thetranscription.app"), "blossom.app.urls"),
        ),
        url(
            "",
            decorator_include(
                force_domain("thetranscription.app"),
                "social_django.urls",
                namespace="social",
            ),
        ),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
