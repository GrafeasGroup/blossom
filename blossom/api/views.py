from django.shortcuts import render
from django.views.generic import TemplateView


def index(request):
    html = 'farts.html'

    return render(request, html)


class PostView(TemplateView):

    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass
