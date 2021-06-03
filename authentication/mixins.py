from django.contrib.auth.mixins import AccessMixin
from django.http import HttpRequest


class GrafeasStaffRequired(AccessMixin):
    """Verify that the current user is a staff member and authenticated."""

    def dispatch(self, request: HttpRequest, *args: object, **kwargs: object) -> object:
        """Check the incoming user's information."""
        if not (
            request.user.is_authenticated
            and (request.user.is_grafeas_staff or request.user.is_staff)
        ):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
