from django.urls import path

from blossom.authentication.urls import urlpatterns as auth_urls
from blossom.website import views

urlpatterns = [
    path('', views.index, name='homepage'),
    path('posts/<int:pk>-<str:slug>/', views.PostDetail.as_view(), name='post_detail'),
    path('newpost', views.PostAdd.as_view()),
    path('posts/<int:pk>-<str:slug>/edit/', views.PostUpdate.as_view(), name='post_update')
]

urlpatterns += auth_urls
