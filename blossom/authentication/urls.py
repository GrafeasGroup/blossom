"""URL configuration for the Authentication application."""
from django.urls import path

from blossom.authentication.views import LoginView, logout_view

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
]
