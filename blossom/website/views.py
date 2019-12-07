from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import render, HttpResponseRedirect, redirect
from django.views.generic import DetailView, UpdateView
from django.views.generic import TemplateView

from blossom.website.forms import PostAddForm, AddUserForm
from blossom.website.helpers import get_additional_context
from blossom.website.models import Post


def index(request):
    c = {
        'posts': Post.objects.filter(
            Q(published=True) &
            Q(standalone_section=False) &
            Q(show_in_news_view=True)
        ).order_by('-date')
    }
    c = get_additional_context(c)
    return render(
        request, 'website/index.html', c
    )


class PostView(TemplateView):

    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass


class PostDetail(DetailView):
    model = Post
    query_pk_and_slug = True
    template_name = 'website/post_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = get_additional_context(context)
        return context


class PostUpdate(LoginRequiredMixin, UpdateView):
    model = Post
    query_pk_and_slug = True
    fields = ['title', 'body', 'published', 'standalone_section', 'header_order']
    template_name = 'website/generic_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = get_additional_context(context)
        return context


class PostAdd(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        c = {
            'form': PostAddForm(),
            'header': 'Add a new post!',
            'subheader': 'Remember to toggle "Published" if you want your post to appear!',
        }
        c = get_additional_context(c)
        return render(request, 'website/generic_form.html', c)

    def post(self, request, *args, **kwargs):
        form = PostAddForm(request.POST)
        if form.is_valid():
            element = form.save(commit=False)
            element.author = request.user
            element.save()
            return HttpResponseRedirect(f"{element.get_absolute_url()}edit")


class AdminView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        c = {
            'posts': Post.objects.all()
        }
        c = get_additional_context(c)
        return render(request, 'website/admin.html', c)


@staff_member_required
def user_create(request):
    if request.method == 'POST':
        f = AddUserForm(request.POST)
        if f.is_valid():
            f.save()
            return redirect('homepage')

    else:
        f = AddUserForm()

    c = {'form': f, 'header': 'Create New User'}

    return render(request, 'website/generic_form.html', c)
