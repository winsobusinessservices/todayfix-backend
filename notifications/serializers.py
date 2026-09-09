from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "data",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields

class NotificationMarkReadSerializer(serializers.Serializer):
    is_read = serializers.BooleanField(default=True, help_text="Set to true to mark the notification as read.")

class NotificationMarkAllReadSerializer(serializers.Serializer):
    pass
