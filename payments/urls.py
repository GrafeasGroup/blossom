from django.urls import path

from payments import views

urlpatterns = [path("", views.charge, name="charge"), path("testing/", views.test_view)]
