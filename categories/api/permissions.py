from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Only ADMIN users can create/update categories
    and subcategories.
    """

    message = "Only ADMIN users can manage categories."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "ADMIN"
        )

