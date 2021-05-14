import rest_framework.permissions as rfperms
from django.contrib.auth.models import AnonymousUser
from django.conf import settings

class AdminApiKeyCustomCheck(rfperms.BasePermission):
    message = "Sorry, this resource can only be accessed by an admin API key."

    def has_permission(self, request, view):
        if settings.OVERRIDE_API_AUTH:
            return True

        if not isinstance(request.user, AnonymousUser):
            if request.user.api_key:
                request_key = None
                if k := request.META.get("Authorization"):
                    request_key = k
                elif k := request.headers.get("Authorization"):
                    request_key = k
                if request_key:
                    request_key = request_key.split()
                    if len(request_key) == 1:
                        # they didn't have the Api-Key bit
                        return
                else:
                    return

                return all(
                    [
                        request_key[0] == "Api-Key",
                        request.user.api_key.is_valid(request_key[1]),
                        request.user.is_grafeas_staff or request.user.is_staff,
                    ]
                )


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
                AdminApiKeyCustomCheck().has_permission(request, view),
            ]
        )
