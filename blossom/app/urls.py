from django.urls import path

from blossom.app import views

urlpatterns = [
    path("", views.choose_transcription, name="choose_transcription"),
    path(
        "transcribe/<int:submission_id>/",
        views.TranscribeSubmission.as_view(),
        name="transcribe_submission",
    ),
    path(
        "transcribe/<int:submission_id>/edit/",
        views.EditSubmissionTranscription.as_view(),
        name="edit_transcription",
    ),
    path("accept_coc/", views.accept_coc, name="accept_coc"),
    path("unclaim/<int:submission_id>/", views.unclaim_submission, name="app_unclaim"),
    path("report/<int:submission_id>/", views.report_submission, name="app_report"),
    path(
        "previous_transcriptions/",
        views.view_previous_transcriptions,
        name="previous_transcriptions",
    ),
]
