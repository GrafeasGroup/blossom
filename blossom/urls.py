from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from authentication.views import LoginView
from website.views import user_create

admin.autodiscover()
admin.site.login = LoginView.as_view()

handler404 = "website.views.handler404"
handler500 = "website.views.handler500"

urlpatterns = [
    path("superadmin/newuser", user_create, name="user_create"),
    path("superadmin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("app/", include("app.urls")),
    path("payments/", include("payments.urls")),
    path("engineering/", include("engineeringblog.urls")),
    path("", include("website.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
