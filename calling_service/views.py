from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from .models import CallSession
from .serializers import CallSessionSerializer
from .permissions import IsCallParticipant
from .services import CallingService

@extend_schema_view(
    list=extend_schema(summary="List call history", tags=["Calling - Service"]),
    create=extend_schema(summary="Initiate a call", tags=["Calling - Service"]),
    retrieve=extend_schema(summary="Retrieve call details", tags=["Calling - Service"]),
    update=extend_schema(summary="Update call", tags=["Calling - Service"]),
    partial_update=extend_schema(summary="Partial update call", tags=["Calling - Service"]),
    destroy=extend_schema(summary="Delete call", tags=["Calling - Service"]),
)
class CallSessionViewSet(viewsets.ModelViewSet):
    """
    Manage call sessions.
    """
    serializer_class = CallSessionSerializer
    permission_classes = [IsAuthenticated, IsCallParticipant]
    lookup_field = "call_session_uuid"

    def get_queryset(self):
        user = self.request.user
        from django.db.models import Q
        return CallSession.objects.filter(Q(caller=user) | Q(receiver=user)).distinct()

    def perform_create(self, serializer):
        conversation = serializer.validated_data['conversation']
        call_type = serializer.validated_data.get('call_type', 'AUDIO')
        call = CallingService.initiate_call(conversation, self.request.user, call_type)
        serializer.instance = call

    @extend_schema(
        summary="Accept an incoming call",
        tags=["Calling - Service"],
        request=None,
        responses={200: CallSessionSerializer}
    )
    @action(detail=True, methods=["post"])
    def accept(self, request, call_session_uuid=None):
        call = self.get_object()
        try:
            updated_call = CallingService.accept_call(call, request.user)
            return Response(self.get_serializer(updated_call).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Reject an incoming call",
        tags=["Calling - Service"],
        request=None,
        responses={200: CallSessionSerializer}
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, call_session_uuid=None):
        call = self.get_object()
        try:
            updated_call = CallingService.reject_call(call, request.user)
            return Response(self.get_serializer(updated_call).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="End an active call",
        tags=["Calling - Service"],
        request=None,
        responses={200: CallSessionSerializer}
    )
    @action(detail=True, methods=["post"])
    def end(self, request, call_session_uuid=None):
        call = self.get_object()
        try:
            updated_call = CallingService.end_call(call, request.user)
            return Response(self.get_serializer(updated_call).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Cancel an initiated call",
        tags=["Calling - Service"],
        request=None,
        responses={200: CallSessionSerializer}
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, call_session_uuid=None):
        call = self.get_object()
        try:
            updated_call = CallingService.cancel_call(call, request.user)
            return Response(self.get_serializer(updated_call).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
