from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Allow only TodayFix ADMIN/super-admin accounts."""

    message = "Administrator access is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == "ADMIN"
            and user.is_staff
        )
