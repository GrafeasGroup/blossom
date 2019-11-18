from django.shortcuts import render
from django.views.generic import TemplateView


def index(request):
    html = 'index.html'

    return render(request, html)
