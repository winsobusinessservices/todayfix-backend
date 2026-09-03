from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from .permissions import IsConversationParticipant
from .services import ChatService
from django.utils import timezone

@extend_schema_view(
    list=extend_schema(summary="List conversations", tags=["Chat - Service"]),
    create=extend_schema(summary="Create conversation", tags=["Chat - Service"]),
    retrieve=extend_schema(summary="Retrieve conversation", tags=["Chat - Service"]),
    update=extend_schema(summary="Update conversation", tags=["Chat - Service"]),
    partial_update=extend_schema(summary="Partial update conversation", tags=["Chat - Service"]),
    destroy=extend_schema(summary="Delete conversation", tags=["Chat - Service"]),
)
class ConversationViewSet(viewsets.ModelViewSet):
    """
    Manage chat conversations.
    Users can only access conversations they are part of.
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    lookup_field = "conversation_uuid"

    def get_queryset(self):
        user = self.request.user
        # Simple queryset, permission class handles object-level auth
        # But we also filter the queryset to avoid returning 404 vs 403 leaks
        from django.db.models import Q
        return Conversation.objects.filter(
            Q(customer=user) | 
            Q(business__owner=user) | 
            (Q(employee__isnull=False) & Q(employee__business__owner=user))
        ).distinct()

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


@extend_schema_view(
    list=extend_schema(summary="List messages in a conversation", tags=["Chat - Service"]),
    create=extend_schema(summary="Send a message", tags=["Chat - Service"]),
    retrieve=extend_schema(summary="Retrieve message", tags=["Chat - Service"]),
    update=extend_schema(summary="Update message", tags=["Chat - Service"]),
    partial_update=extend_schema(summary="Partial update message", tags=["Chat - Service"]),
    destroy=extend_schema(summary="Delete message", tags=["Chat - Service"]),
)
class MessageViewSet(viewsets.ModelViewSet):
    """
    Manage messages within a conversation.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "message_uuid"

    def get_permissions(self):
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        # Messages from conversations the user can access
        from django.db.models import Q
        return Message.objects.filter(
            Q(conversation__customer=user) | 
            Q(conversation__business__owner=user)
        ).distinct()

    def perform_create(self, serializer):
        conversation = serializer.validated_data['conversation']
        
        # Verify access
        permission = IsConversationParticipant()
        if not permission.has_object_permission(self.request, self, conversation):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have access to this conversation.")
            
        serializer.save(sender=self.request.user)

    def perform_destroy(self, instance):
        if instance.sender != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own messages.")
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at"])

    def perform_update(self, serializer):
        if serializer.instance.sender != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own messages.")
        serializer.save()

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
            return Response({"success": False, "detail": "Cannot mark own message as read"}, status=400)
            
        message.is_read = True
        message.read_at = timezone.now()
        message.save(update_fields=["is_read", "read_at"])
        return Response({"success": True})
