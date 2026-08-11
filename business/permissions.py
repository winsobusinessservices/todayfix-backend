from rest_framework.permissions import BasePermission

from accounts.choices import UserRole


class IsAdminRole(BasePermission):

    message = "Admin access is required."

    def has_permission(
        self,
        request,
        view,
    ):

        return (
            bool(
                request.user
                and request.user.is_authenticated
            )
            and getattr(
                request.user,
                "role",
                None,
            )
            == UserRole.ADMIN
        )


        