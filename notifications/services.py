import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)

class NotificationService:
    
    @classmethod
    def create(cls, recipient, notification_type, title, message, data=None):
        """
        Creates a notification safely. If creation fails, it logs the error but does not raise it,
        so the calling transaction is not aborted for a notification failure.
        It also attempts to broadcast the notification via WebSockets.
        """
        if data is None:
            data = {}

        try:
            notification = Notification.objects.create(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                data=data
            )
            
            # Broadcast to WebSocket
            cls._send_real_time(notification)
            
            return notification
        except Exception as e:
            logger.error(f"Failed to create notification for {recipient}: {e}", exc_info=True)
            return None

    @classmethod
    def _send_real_time(cls, notification):
        """
        Sends the notification payload to the recipient's isolated WebSocket group.
        """
        try:
            channel_layer = get_channel_layer()
            group_name = f"notifications_user_{notification.recipient.user_uuid}"
            
            serializer = NotificationSerializer(notification)
            payload = {
                "type": "notification_message",
                "event": "notification",
                "notification": serializer.data
            }
            
            async_to_sync(channel_layer.group_send)(
                group_name,
                payload
            )
        except Exception as e:
            logger.error(f"Failed to send real-time notification {notification.id}: {e}", exc_info=True)
