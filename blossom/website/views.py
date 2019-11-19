from django.shortcuts import render
from django.views.generic import TemplateView

from blossom.website.models import Post
from django.db.models import Q


def index(request):
    return render(
        request, 'website/index.html', {
            'posts': Post.objects.filter(Q(published=True) & Q(standalone_section=True))
        }
    )


class PostView(TemplateView):

    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass
