from django.urls import path

from blossom.website import views

urlpatterns = [
    path('', views.index, name='homepage'),
    path('posts/<int:pk>-<str:slug>/', views.PostDetail.as_view(), name='post_detail'),
    path('newpost', views.PostAdd.as_view())

]
