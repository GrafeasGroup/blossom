import rest_framework.permissions as rfperms
from django.contrib.auth.models import AnonymousUser

from blossom.api.models import Volunteer


class APIKeyVolunteerAdminCheck(rfperms.BasePermission):
    message = "ack"

    def has_permission(self, request, view):
        if not isinstance(request.user, AnonymousUser):
            if v := Volunteer.objects.filter(staff_account=request.user).first():
                return v.api_key.is_valid(request.headers.get("X-Api-Key"))


class BlossomApiPermission(rfperms.BasePermission):

    # For some reason, combining the different auth patterns in the settings
    # file fails miserably and will default to HasAPIKey if it's enabled.
    # I've spent far too long screwing with this, so here's a permission
    # class that manually checks both of them and returns true if either one
    # of them is valid.

    message = "Sorry, this resource can only be accessed by an admin."
    def has_permission(self, request, view):
        return any(
            [
                rfperms.IsAdminUser().has_permission(request, view),
                APIKeyVolunteerAdminCheck().has_permission(request, view),
            ]
        )
