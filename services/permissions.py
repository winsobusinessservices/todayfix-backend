from rest_framework.permissions import BasePermission

from accounts.choices import UserRole


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

        from business.models import BusinessProfile

        return BusinessProfile.objects.filter(
            owner=user,
            is_active=True,
        ).exists()


class IsServiceOwner(BasePermission):
    """
    Object-level permission: the requesting user
    must own the service's business profile.
    """

    message = "You can only modify your own services."

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        return obj.business.owner == request.user
