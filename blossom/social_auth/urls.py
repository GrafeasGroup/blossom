from django.conf.urls import url
from django.conf.urls import include

urlpatterns = [url("", include("social_django.urls", namespace="social"))]
