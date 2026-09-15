from rest_framework.permissions import BasePermission, IsAuthenticated


class IsWalletOwner(BasePermission):
    """
    Ensures that authenticated users can only interact with their own Fix-Coin resources.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "wallet"):
            return obj.wallet.user == request.user
        return False
