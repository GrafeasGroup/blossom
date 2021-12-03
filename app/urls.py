from django.urls import path

from app import views

urlpatterns = [
    path("practice/", views.PracticeTranscription.as_view()),
    path("", views.index_test),
]
