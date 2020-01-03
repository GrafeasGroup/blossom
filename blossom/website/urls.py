from django.urls import path

from blossom.authentication.urls import urlpatterns as auth_urls
from blossom.website import views
from blossom.website.helpers import grafeas_staff_required

urlpatterns = [
    path("", views.index, name="homepage"),
    path("posts/<int:pk>-<str:slug>/", views.PostDetail.as_view(), name="post_detail"),
    path(
        "newpost", grafeas_staff_required(views.PostAdd.as_view()), name="post_create"
    ),
    path(
        "posts/<int:pk>-<str:slug>/edit/",
        grafeas_staff_required(views.PostUpdate.as_view()),
        name="post_update",
    ),
    path("admin/", grafeas_staff_required(views.AdminView.as_view()), name="admin_view")
    # path('admin/', views.AdminView.as_view(), name='admin_view')
]

urlpatterns += auth_urls
