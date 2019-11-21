import rest_framework.permissions as rfperms
import rest_framework_api_key.permissions as rfakperms


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
                rfakperms.HasAPIKey().has_permission(request, view),
            ]
        )
