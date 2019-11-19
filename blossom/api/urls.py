from django.urls import path

from blossom.api import views

urlpatterns = [
    path('', views.index, name='homepage'),
]
