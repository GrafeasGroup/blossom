from django.shortcuts import render
from django.db.models import Q

from blossom.website.models import Post

def index(request):

    p = Post.objects.filter(Q(published=True) & Q(engineeringblogpost=True))

    return render(request, 'website/index.html', {'posts': p})
