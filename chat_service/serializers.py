from rest_framework import serializers
from .models import Conversation, Message

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            "message_uuid",
            "conversation",
            "sender",
            "sender_name",
            "message_type",
            "text",
            "attachment",
            "reply_to",
            "is_read",
            "read_at",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "message_uuid",
            "sender",
            "is_read",
            "read_at",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        
    def get_sender_name(self, obj):
        if obj.sender:
            return f"{obj.sender.first_name} {obj.sender.last_name}".strip()
        return "System"


class ConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            "conversation_uuid",
            "booking_type",
            "scheduled_booking",
            "instant_booking",
            "customer",
            "business",
            "employee",
            "status",
            "closed_at",
            "archived_at",
            "created_at",
            "updated_at",
            "last_message",
            "unread_count",
        ]
        read_only_fields = [
            "conversation_uuid",
            "customer",
            "business",
            "employee",
            "booking_type",
            "scheduled_booking",
            "instant_booking",
            "status",
            "closed_at",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        
    def get_last_message(self, obj):
        last_msg = obj.messages.order_by("-created_at").first()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None
        
    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        return obj.messages.exclude(sender=request.user).filter(is_read=False).count()
