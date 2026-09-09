from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationMarkReadSerializer,
    NotificationMarkAllReadSerializer,
)

class NotificationListView(generics.ListAPIView):
    """
    List all notifications for the authenticated user.
    Ordered by newest first.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="List user notifications",
        description="Returns a paginated list of notifications for the authenticated user, newest first.",
        responses={200: NotificationSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by("-created_at")


class NotificationMarkReadView(generics.UpdateAPIView):
    """
    Mark a specific notification as read.
    """
    serializer_class = NotificationMarkReadSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @extend_schema(
        tags=["Notifications"],
        summary="Mark notification as read",
        description="Marks a specific notification as read and sets the read_at timestamp.",
        request=NotificationMarkReadSerializer,
        responses={
            200: NotificationSerializer,
            404: OpenApiResponse(description="Notification not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        notification = self.get_object()
        
        # We only care about setting it to read
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
            
        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)


class NotificationMarkAllReadView(APIView):
    """
    Mark all unread notifications as read for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Mark all notifications as read",
        description="Marks all unread notifications for the authenticated user as read.",
        request=NotificationMarkAllReadSerializer,
        responses={
            200: OpenApiResponse(description="Success response", examples=[{"status": "success", "updated_count": 5}]),
        }
    )
    def patch(self, request, *args, **kwargs):
        unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False)
        updated_count = unread_notifications.update(is_read=True, read_at=timezone.now())
        return Response({"status": "success", "updated_count": updated_count}, status=status.HTTP_200_OK)


class NotificationDeleteView(generics.DestroyAPIView):
    """
    Delete a specific notification.
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @extend_schema(
        tags=["Notifications"],
        summary="Delete a notification",
        description="Permanently deletes the specified notification.",
        responses={
            204: OpenApiResponse(description="No Content"),
            404: OpenApiResponse(description="Not Found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
