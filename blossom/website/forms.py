from django import forms
from django.core.exceptions import ValidationError

from blossom.authentication.models import BlossomUser
from blossom.website.models import Post


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class PostAddForm(forms.ModelForm):
    # is AM / PM not being detected correctly?
    date = forms.DateTimeField(
        required=False,
        input_formats=["%m/%d/%Y, %H:%M %p"],
        widget=forms.DateTimeInput(
            attrs={
                "class": "form-control datetimepicker-input",
                "data-target": "#datetimepicker1",
            }
        ),
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "body",
            "published",
            "date",
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
    def clean_username(self) -> str:
        """Validate username."""
        username = self.cleaned_data["username"].lower()
        resp = BlossomUser.objects.filter(username=username)
        if resp.count():
            raise ValidationError("Username already exists")
        return username

    def clean_email(self) -> str:
        """Validate email."""
        email = self.cleaned_data["email"].lower()
        resp = BlossomUser.objects.filter(email=email)
        if resp.count():
            raise ValidationError("Email already exists")
        return email

    def save(self, commit: bool = True) -> BlossomUser:
        """Save the instance."""
        user = BlossomUser.objects.create_user(
            self.cleaned_data["username"],
            self.cleaned_data["email"],
            self.cleaned_data["password"],
            is_superuser=self.cleaned_data["is_superuser"],
            is_staff=self.cleaned_data["is_superuser"],
        )
        return user
