from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm

from blossom.authentication.models import BlossomUser


class BlossomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = BlossomUser


class BlossomUserAdmin(UserAdmin):
    form = BlossomUserChangeForm

    fieldsets = UserAdmin.fieldsets + (
        (
            None,
            {
                "fields": (
                    "last_update_time",
                    "is_grafeas_staff",
                    "is_volunteer",
                    "accepted_coc",
                    "api_key",
                    "blocked",
                )
            },
        ),
    )


# Register your models here.
admin.site.register(BlossomUser, BlossomUserAdmin)
