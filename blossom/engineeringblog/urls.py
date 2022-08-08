from django.urls import path

from blossom.engineeringblog import views
from blossom.website.urls import urlpatterns as website_urls

urlpatterns = [
    path("", views.index, name="blog_index"),
]

# This is so that normal operations on posts, like the detail view, editing,
# and more, will continue to work under the new subdomain.
urlpatterns += website_urls
