import rest_framework.permissions as rfperms
from django.contrib.auth.models import AnonymousUser


class APIKeyCustomCheck(rfperms.BasePermission):
    message = "Sorry, this resource can only be accessed by an admin or with a valid"\
        " api key."

    def has_permission(self, request, view):
        if not isinstance(request.user, AnonymousUser):
            if request.user.api_key:
                return request.user.api_key.is_valid(request.headers.get("X-Api-Key"))
            elif request.user.is_grafeas_staff or request.user.is_staff:
                return True

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
                APIKeyCustomCheck().has_permission(request, view),
            ]
        )


class AdminApiKeyCustomCheck(rfperms.BasePermission):
    message = "Sorry, this resource can only be accessed by an admin API key."

    def has_permission(self, request, view):
        if not isinstance(request.user, AnonymousUser):
            if request.user.api_key:
                return all([
                    request.user.api_key.is_valid(request.headers.get("X-Api-Key")),
                    request.user.is_grafeas_staff,
                ])
