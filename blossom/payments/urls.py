from django.urls import path

from blossom.payments import views

urlpatterns = [path("", views.charge, name="charge")]
