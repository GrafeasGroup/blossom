from django import forms
from django.core.exceptions import ValidationError

from authentication.models import BlossomUser
from website.models import Post


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class PostAddForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = [
            "title",
            "body",
            "published",
            "standalone_section",
            "engineeringblogpost",
            "header_order",
        ]


class AddUserForm(forms.Form):
    # https://overiq.com/django-1-10/django-creating-users-using-usercreationform/
    username = forms.CharField(label="Enter Username", min_length=4, max_length=150)
    email = forms.EmailField(label="Enter email")
    password = forms.CharField(label="Enter password", widget=forms.PasswordInput)
    is_superuser = forms.BooleanField(label="Is this user a superuser?", required=False)

    # the clean functions will be run automatically on save
    def clean_username(self):
        username = self.cleaned_data["username"].lower()
        r = BlossomUser.objects.filter(username=username)
        if r.count():
            raise ValidationError("Username already exists")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        r = BlossomUser.objects.filter(email=email)
        if r.count():
            raise ValidationError("Email already exists")
        return email

    def save(self, commit=True):
        user = BlossomUser.objects.create_user(
            self.cleaned_data["username"],
            self.cleaned_data["email"],
            self.cleaned_data["password"],
            is_superuser=self.cleaned_data["is_superuser"],
            is_staff=self.cleaned_data["is_superuser"],
        )
        return user
