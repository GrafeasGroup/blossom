from django.urls import path

from blossom.engineeringblog import views

urlpatterns = [
    path('', views.index, name="blog_index"),
]
