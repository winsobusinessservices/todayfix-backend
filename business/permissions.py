from rest_framework.permissions import BasePermission

from accounts.choices import UserRole
from .choices import BusinessType

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


class IsApprovedBusiness(BasePermission):
    """
    Allow access only to users who have an active
    approved business profile.
    """

    message = (
        "You must have an approved, active "
        "business profile to perform this action."
    )

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.role != UserRole.BUSINESS:
            return False

        from .models import BusinessProfile

        return BusinessProfile.objects.filter(
            owner=user,
            is_active=True,
        ).exists()

class IsEmployeeManagementAllowed(BasePermission):
    """
    Allow employee management only for COMPANY
    and INVESTOR businesses.
    """

    message = (
        "Employee management is not available "
        "for Individual businesses."
    )

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.role != UserRole.BUSINESS:
            return False

        from .models import BusinessProfile

        return BusinessProfile.objects.filter(
            owner=user,
            is_active=True,
            business_type__in=[
                BusinessType.COMPANY,
                BusinessType.INVESTOR,
            ],
        ).exists()
