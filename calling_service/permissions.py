from rest_framework import permissions

class IsCallParticipant(permissions.BasePermission):
    """
    Object-level permission to allow call participants to access/modify a call session.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if not user.is_authenticated:
            return False
            
        if user == obj.caller or user == obj.receiver:
            return True
            
        return False
