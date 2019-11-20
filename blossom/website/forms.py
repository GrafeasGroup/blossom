from django import forms

from blossom.website.models import Post

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class PostAddForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'body', 'published', 'standalone_section', 'header_order']
