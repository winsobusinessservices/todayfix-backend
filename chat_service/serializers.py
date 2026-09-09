from rest_framework import serializers
from .models import Conversation, Message
from .choices import MessageType

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    is_edited = serializers.SerializerMethodField()
    
    conversation = serializers.SlugRelatedField(
        slug_field="conversation_uuid",
        queryset=Conversation.objects.all(),
    )
    
    reply_to = serializers.SlugRelatedField(
        slug_field="message_uuid",
        queryset=Message.objects.all(),
        required=False,
        allow_null=True,
    )
    
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
            "is_edited",
            "edited_at",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "message_uuid",
            "sender",
            "is_read",
            "read_at",
            "is_edited",
            "edited_at",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        
    def get_sender_name(self, obj):
        if obj.sender:
            return f"{obj.sender.first_name} {obj.sender.last_name}".strip()
        return "System"

    def get_is_edited(self, obj):
        return obj.edited_at is not None

    def validate(self, attrs):
        message_type = attrs.get('message_type', getattr(self.instance, 'message_type', MessageType.TEXT))
        text = attrs.get('text', getattr(self.instance, 'text', ''))
        attachment = attrs.get('attachment', getattr(self.instance, 'attachment', None))
        
        # 1. Message Type Validation
        if message_type == MessageType.TEXT:
            if not str(text).strip():
                raise serializers.ValidationError({"text": "Text content is required for text messages."})
            if attachment:
                raise serializers.ValidationError({"attachment": "Attachments are not allowed for text messages."})
        elif message_type in [MessageType.IMAGE, MessageType.FILE]:
            if not attachment:
                raise serializers.ValidationError({"attachment": f"Attachment is required for {message_type} messages."})
                
        # 2. Reply To Validation
        reply_to = attrs.get('reply_to', getattr(self.instance, 'reply_to', None))
        conversation = attrs.get('conversation', getattr(self.instance, 'conversation', None))
        if reply_to and conversation:
            if reply_to.conversation != conversation:
                raise serializers.ValidationError({"reply_to": "Reply must belong to the same conversation."})
            if reply_to.deleted_at is not None:
                raise serializers.ValidationError({"reply_to": "Cannot reply to a deleted message."})
                
        return attrs


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
        # Do not expose deleted messages
        last_msg = obj.messages.filter(deleted_at__isnull=True).order_by("-created_at").first()
        if last_msg:
            return MessageSerializer(last_msg, context=self.context).data
        return None
        
    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        return obj.messages.filter(deleted_at__isnull=True).exclude(sender=request.user).filter(is_read=False).count()
