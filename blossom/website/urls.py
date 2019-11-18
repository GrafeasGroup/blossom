from django.urls import path

from blossom.website import views

urlpatterns = [
    path('', views.index, name='homepage'),
]
