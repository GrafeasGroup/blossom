from django.urls import path

from authentication.urls import urlpatterns as auth_urls
from website import views
from website.helpers import grafeas_staff_required

urlpatterns = [
    path("", views.index, name="homepage"),
    # compatibility layer to allow old style URLs to resolve to slug-only.
    # Must be above regular version.
    path(
        "posts/<int:pk>-<str:slug>/",
        views.post_view_redirect,
        name="post_detail_redirect",
    ),
    path("posts/<str:slug>/", views.PostDetail.as_view(), name="post_detail"),
    path(
        "newpost", grafeas_staff_required(views.PostAdd.as_view()), name="post_create"
    ),
    path(
        "posts/<str:slug>/edit/",
        grafeas_staff_required(views.PostUpdate.as_view()),
        name="post_update",
    ),
    path(
        "admin/", grafeas_staff_required(views.AdminView.as_view()), name="admin_view"
    ),
]

urlpatterns += auth_urls
