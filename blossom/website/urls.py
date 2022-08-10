from django.urls import path

from blossom.website import views

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
    path("newpost", views.PostAdd.as_view(), name="post_create"),
    path(
        "posts/<str:slug>/edit/",
        views.PostUpdate.as_view(),
        name="post_update",
    ),
    path("admin/", views.AdminView.as_view(), name="admin_view"),
]
