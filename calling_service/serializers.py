from rest_framework import serializers
from .models import CallSession
from chat_service.models import Conversation

class CallSessionSerializer(serializers.ModelSerializer):
    caller_name = serializers.SerializerMethodField()
    receiver_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CallSession
        fields = [
            "call_session_uuid",
            "conversation",
            "caller",
            "caller_name",
            "receiver",
            "receiver_name",
            "call_type",
            "status",
            "provider_call_id",
            "started_at",
            "answered_at",
            "ended_at",
            "duration_seconds",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "call_session_uuid",
            "caller",
            "receiver",
            "status",
            "provider_call_id",
            "started_at",
            "answered_at",
            "ended_at",
            "duration_seconds",
            "created_at",
            "updated_at",
        ]

    def get_caller_name(self, obj):
        if obj.caller:
            return f"{obj.caller.first_name} {obj.caller.last_name}".strip()
        return "Unknown"

    def get_receiver_name(self, obj):
        if obj.receiver:
            return f"{obj.receiver.first_name} {obj.receiver.last_name}".strip()
        return "Unknown"
        
    def validate_conversation(self, value):
        # Validate that the conversation belongs to the user
        request = self.context.get("request")
        user = request.user
        
        # We reuse the permission logic or explicitly check here
        has_access = False
        if user == value.customer:
            has_access = True
        elif value.employee and getattr(user, 'employee_profile', None) == value.employee:
            has_access = True
        elif user == value.business.owner:
            has_access = True
            
        if not has_access:
            raise serializers.ValidationError("You do not have access to this conversation.")
            
        return value
