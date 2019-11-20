from django.db.models import Q
from django.shortcuts import render, HttpResponseRedirect, reverse
from django.views.generic import TemplateView
from django.views.generic import DetailView
from django.contrib.auth import login, logout

from blossom.website.models import Post
from blossom.website.forms import LoginForm, PostAddForm
from blossom.authentication.custom_auth import EmailBackend

def index(request):
    return render(
        request, 'website/index.html', {
            'posts': Post.objects.filter(Q(published=True) & Q(standalone_section=False)),
            'navbar': Post.objects.filter(Q(published=True) & Q(standalone_section=True))
        }
    )


class PostView(TemplateView):

    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass


class LoginView(TemplateView):
    def get(self, request, *args, **kwargs):
        form = LoginForm()
        return render(request, 'website/generic_form.html', {'form': form})

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if user := EmailBackend().authenticate(
                    username=data.get('email'), password=data.get('password')
            ):
                login(request, user)
                return HttpResponseRedirect(request.GET.get('next'))
            return HttpResponseRedirect('/')


class PostDetail(DetailView):
    model = Post
    query_pk_and_slug = True
    template_name = 'website/post_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['navbar'] = (
            Post.objects.filter(Q(published=True) & Q(standalone_section=True))
        )
        return context


class PostAdd(TemplateView):
    def get(self, request, *args, **kwargs):
        return render(request, 'website/generic_form.html', {
            'form': PostAddForm(),
            'header': 'Add a new post!',
            'subheader': 'This will add a new post.',
            'navbar': (
                Post.objects.filter(Q(published=True) & Q(standalone_section=True))
            )
        })
