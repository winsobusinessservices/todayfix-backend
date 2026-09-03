from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

class IsConversationParticipant(permissions.BasePermission):
    """
    Object-level permission to only allow conversation participants to access it.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if not user.is_authenticated:
            return False
            
        if user == obj.customer:
            return True
            
        if obj.employee and getattr(user, 'employee_profile', None) == obj.employee:
            return True
            
        # Check if user is the business owner
        if user == obj.business.owner:
            return True
            
        return False
