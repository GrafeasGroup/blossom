from django.urls import path

from authentication.views import LoginView, LogoutView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView, name="logout"),
]
