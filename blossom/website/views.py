from django.db.models import Q
from django.shortcuts import render, HttpResponseRedirect, reverse
from django.views.generic import TemplateView
from django.views.generic import DetailView, UpdateView
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin

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
                return HttpResponseRedirect(request.GET.get('next', '/'))
            return HttpResponseRedirect('/')


def LogoutView(request):
    logout(request)
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


class PostUpdate(LoginRequiredMixin, UpdateView):
    model = Post
    query_pk_and_slug = True
    fields = ['title', 'body', 'published', 'standalone_section', 'header_order']
    template_name = 'website/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['navbar'] = (
            Post.objects.filter(Q(published=True) & Q(standalone_section=True))
        )
        return context


class PostAdd(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        return render(request, 'website/generic_form.html', {
            'form': PostAddForm(),
            'header': 'Add a new post!',
            'subheader': 'Remember to toggle "Published" if you want your post to appear!',
            'navbar': (
                Post.objects.filter(Q(published=True) & Q(standalone_section=True))
            )
        })

    def post(self, request, *args, **kwargs):
        form = PostAddForm(request.POST)
        if form.is_valid():
            element = form.save(commit=False)
            element.author = request.user
            element.save()
            return HttpResponseRedirect(f"{element.get_absolute_url()}edit")
