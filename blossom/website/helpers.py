from django.db.models import Q

from blossom.website.models import Post

def get_additional_context(context):
    context['navbar'] = Post.objects.filter(Q(published=True) & Q(standalone_section=True))
    context['tos'] = Post.objects.get(slug='terms-of-service')
    return context
