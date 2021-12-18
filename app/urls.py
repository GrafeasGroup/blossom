from django.urls import path

from app import views

urlpatterns = [
    path("", views.choose_transcription, name="choose_transcription"),
    path(
        "transcribe/<int:submission_id>/",
        views.TranscribeSubmission.as_view(),
        name="transcribe_submission",
    ),
    path("accept_coc/", views.accept_coc, name="accept_coc"),
    path("unclaim/<int:submission_id>/", views.unclaim_submission, name="app_unclaim"),
]
