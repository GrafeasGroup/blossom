"""
This file is only called from django-hosts and is not referenced anywhere else.
"""
from django.urls import path
from django.urls import include
from django.contrib.auth.decorators import login_required


# https://gist.github.com/garrypolley/3762045#gistcomment-2089316
def process_url_patterns(patterns, *decorators):
    """ Recursively look through patterns for views and apply decorators """
    for url_pattern in patterns:
        if hasattr(url_pattern, "url_patterns"):
            process_url_patterns(url_pattern.url_patterns, *decorators)
        else:
            for decorator in decorators:
                # print("Decorating {} with {}".format(url_pattern, decorator))
                url_pattern.callback = decorator(url_pattern.callback)


def decorated_include(urls, *decorators):
    """
    Used to decorate all urls in a 3rd party app with specific decorators
    """
    urls_to_decorate, app_name, namespace = include(urls)
    process_url_patterns(urls_to_decorate.urlpatterns, *decorators)
    return urls_to_decorate, app_name, namespace


urlpatterns = [
    path("notifications/", include("django_nyt.urls")),
    path("", decorated_include("wiki.urls", login_required)),
]
