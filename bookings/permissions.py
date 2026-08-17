from rest_framework.permissions import BasePermission

from accounts.choices import UserRole


class IsBookingUser(BasePermission):
    """
    Allow access only if the user is the customer who
    made the booking.
    """
    message = "You can only access your own bookings."

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsBookingBusiness(BasePermission):
    """
    Allow access only if the user owns the business
    that the booking is for.
    """
    message = "You can only access bookings for your business."

    def has_object_permission(self, request, view, obj):
        return obj.business.owner == request.user
