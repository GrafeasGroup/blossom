from django.urls import path

from blossom.slack_conn import views

urlpatterns = [path('slack/endpoint/', views.slack_endpoint)]
