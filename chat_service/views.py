from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, OpenApiTypes
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from .permissions import IsConversationParticipant
from .services import ChatService
from .choices import ConversationStatus
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json

def _broadcast_message_event(conversation_uuid, event_type, message_data):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    group_name = f"chat_{conversation_uuid}"
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "chat_message",
            "message": {
                "type": event_type,
                "data": message_data
            }
        }
    )

@extend_schema_view(

    list=extend_schema(summary="List conversations", tags=["Chat - Service"]),
    create=extend_schema(summary="Create conversation", tags=["Chat - Service"]),
    retrieve=extend_schema(summary="Retrieve conversation", tags=["Chat - Service"]),
    update=extend_schema(summary="Update conversation", tags=["Chat - Service"]),
    partial_update=extend_schema(summary="Partial update conversation", tags=["Chat - Service"]),
    destroy=extend_schema(summary="Delete conversation", tags=["Chat - Service"]),
)
class ConversationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Manage chat conversations.
    Users can only access conversations they are part of.
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    lookup_field = "conversation_uuid"

    def get_queryset(self):
        user = self.request.user
        from django.db.models import Q
        return Conversation.objects.filter(
            Q(customer=user) | 
            Q(business__owner=user) | 
            (Q(employee__isnull=False) & Q(employee__business__owner=user))
        ).distinct()

    @extend_schema(
        summary="Close conversation",
        tags=["Chat - Conversations"],
        request=None,
        responses={200: ConversationSerializer}
    )
    @action(detail=True, methods=["patch"])
    def close(self, request, conversation_uuid=None):
        conversation = self.get_object()
        if conversation.status == ConversationStatus.ARCHIVED:
            return Response({"detail": "Cannot close an archived conversation."}, status=status.HTTP_400_BAD_REQUEST)
        if conversation.status != ConversationStatus.CLOSED:
            conversation.status = ConversationStatus.CLOSED
            conversation.closed_at = timezone.now()
            conversation.save(update_fields=["status", "closed_at"])
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)

    @extend_schema(
        summary="Archive conversation",
        tags=["Chat - Conversations"],
        request=None,
        responses={200: ConversationSerializer}
    )
    @action(detail=True, methods=["patch"])
    def archive(self, request, conversation_uuid=None):
        conversation = self.get_object()
        if conversation.status == ConversationStatus.CLOSED:
            return Response({"detail": "Cannot archive a closed conversation."}, status=status.HTTP_400_BAD_REQUEST)
        if conversation.status != ConversationStatus.ARCHIVED:
            conversation.status = ConversationStatus.ARCHIVED
            conversation.archived_at = timezone.now()
            conversation.save(update_fields=["status", "archived_at"])
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)

    @extend_schema(
        summary="Mark conversation as read",
        tags=["Chat - Service"],
        request=None,
        responses={200: OpenApiResponse(description="Messages marked as read")}
    )
    @action(detail=True, methods=["post"])
    def read(self, request, conversation_uuid=None):
        conversation = self.get_object()
        count = ChatService.mark_conversation_read(conversation, request.user)
        return Response({"success": True, "marked_read": count})

    @extend_schema(
        summary="List messages in a conversation",
        tags=["Chat - Messages"],
        methods=["GET"],
        responses={200: MessageSerializer(many=True)}
    )
    @extend_schema(
        summary="Send a message",
        tags=["Chat - Messages"],
        methods=["POST"],
        request=MessageSerializer,
        responses={201: MessageSerializer}
    )
    @action(detail=True, methods=["get", "post"])
    def messages(self, request, conversation_uuid=None):
        conversation = self.get_object()
        if request.method == "GET":
            messages = conversation.messages.filter(deleted_at__isnull=True).order_by("-created_at")
            page = self.paginate_queryset(messages)
            if page is not None:
                serializer = MessageSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            serializer = MessageSerializer(messages, many=True, context={'request': request})
            return Response(serializer.data)
        
        elif request.method == "POST":
            # Pass conversation via serializer logic
            data = request.data.copy()
            data['conversation'] = conversation.conversation_uuid
            serializer = MessageSerializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            message = serializer.save(sender=request.user)
            
            # Broadcast
            _broadcast_message_event(conversation.conversation_uuid, "message.created", serializer.data)
            
            # Notification Integration
            recipient = conversation.business.owner if request.user == conversation.customer else conversation.customer
            if recipient and recipient != request.user:
                from notifications.services import NotificationService
                from notifications.choices import NotificationType
                NotificationService.create(
                    recipient=recipient,
                    notification_type=NotificationType.NEW_CHAT_MESSAGE,
                    title="New Message",
                    message=f"New message from {request.user.first_name}.",
                    data={"conversation_id": str(conversation.conversation_uuid), "message_id": str(message.message_uuid)}
                )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(

    list=extend_schema(summary="List messages in a conversation", tags=["Chat - Service"]),
    create=extend_schema(summary="Send a message", tags=["Chat - Service"]),
    retrieve=extend_schema(summary="Retrieve message", tags=["Chat - Service"]),
    update=extend_schema(summary="Update message", tags=["Chat - Service"]),
    partial_update=extend_schema(summary="Partial update message", tags=["Chat - Service"]),
    destroy=extend_schema(summary="Delete message", tags=["Chat - Service"]),
)
class MessageViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    Manage specific messages.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "message_uuid"

    def get_queryset(self):
        user = self.request.user
        from django.db.models import Q
        return Message.objects.filter(
            deleted_at__isnull=True
        ).filter(
            Q(conversation__customer=user) | 
            Q(conversation__business__owner=user)
        ).distinct()

    def perform_destroy(self, instance):
        if instance.sender != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own messages.")
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at"])
        serializer = self.get_serializer(instance)
        _broadcast_message_event(instance.conversation.conversation_uuid, "message.deleted", serializer.data)

    def perform_update(self, serializer):
        if serializer.instance.sender != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own messages.")
        if serializer.instance.deleted_at is not None:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Cannot edit a deleted message.")
            
        serializer.save(edited_at=timezone.now())
        _broadcast_message_event(serializer.instance.conversation.conversation_uuid, "message.updated", serializer.data)

    @extend_schema(
        summary="Mark a specific message as read",
        tags=["Chat - Service"],
        request=None,
        responses={200: OpenApiResponse(description="Message marked as read")}
    )
    @action(detail=True, methods=["post"])
    def read(self, request, message_uuid=None):
        message = self.get_object()
        if message.sender == request.user:
            return Response({"success": False, "detail": "Cannot mark own message as read"}, status=status.HTTP_400_BAD_REQUEST)
            
        message.is_read = True
        message.read_at = timezone.now()
        message.save(update_fields=["is_read", "read_at"])
        return Response({"success": True})
