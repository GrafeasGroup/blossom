from django.contrib.auth.mixins import AccessMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from blossom.utils.auth import grafeas_staff_required


class CSRFExemptMixin(object):
    # https://stackoverflow.com/a/53065028
    @method_decorator(csrf_exempt)
    def dispatch(self, *args: object, **kwargs: object) -> object:
        """Apply the decorator to the class."""
        return super().dispatch(*args, **kwargs)


class GrafeasStaffRequired(AccessMixin):
    """Verify that the current user is a staff member and authenticated."""

    @method_decorator(grafeas_staff_required)
    def dispatch(self, *args: object, **kwargs: object) -> object:
        """Check the incoming user's information."""
        return super().dispatch(*args, **kwargs)
