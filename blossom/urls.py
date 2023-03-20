from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from blossom.authentication.views import LoginView
from blossom.website.views import user_create

admin.autodiscover()
admin.site.login = LoginView.as_view()

handler404 = "blossom.website.views.handler404"
handler500 = "blossom.website.views.handler500"

urlpatterns = [
    path("superadmin/newuser", user_create, name="user_create"),
    path("superadmin/", admin.site.urls),
    path("", include("blossom.authentication.urls")),
    path("api/", include("blossom.api.urls")),
    path("payments/", include("blossom.payments.urls")),
    path("engineering/", include("blossom.engineeringblog.urls")),
    path("", include("blossom.website.urls")),
]

if settings.ENABLE_APP:
    urlpatterns += [
        path("app/", include("blossom.app.urls")),
        url("app_login/", include("social_django.urls")),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
