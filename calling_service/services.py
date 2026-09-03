from django.utils import timezone
from .models import CallSession
from .choices import CallStatus
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class CallingService:
    @staticmethod
    def _notify_chat(conversation, event_type, call_data):
        """
        Helper to send a websocket message to the conversation group.
        """
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
            
        group_name = f"chat_{conversation.conversation_uuid}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "call_event",
                "event_type": event_type,
                "call_data": call_data,
            }
        )

    @staticmethod
    def initiate_call(conversation, caller, call_type="AUDIO"):
        if conversation.status != "ACTIVE":
            raise ValueError("Conversation is not active.")
            
        # Determine receiver
        receiver = None
        if caller == conversation.customer:
            # Caller is customer, receiver is business owner or employee (if we had employee auth)
            receiver = conversation.business.owner
        else:
            receiver = conversation.customer
            
        call = CallSession.objects.create(
            conversation=conversation,
            caller=caller,
            receiver=receiver,
            call_type=call_type,
            status=CallStatus.INITIATED,
        )
        
        # Notify via websocket
        CallingService._notify_chat(conversation, "incoming_call", {
            "call_id": str(call.call_session_uuid),
            "caller_id": str(caller.user_uuid),
        })
        
        return call

    @staticmethod
    def accept_call(call: CallSession, user):
        if call.status not in [CallStatus.INITIATED, CallStatus.RINGING]:
            raise ValueError("Call cannot be accepted in its current state.")
        if user != call.receiver:
            raise ValueError("Only the receiver can accept the call.")
            
        call.status = CallStatus.ACCEPTED
        call.answered_at = timezone.now()
        call.save()
        
        CallingService._notify_chat(call.conversation, "call_accepted", {
            "call_id": str(call.call_session_uuid)
        })
        return call

    @staticmethod
    def reject_call(call: CallSession, user):
        if call.status not in [CallStatus.INITIATED, CallStatus.RINGING]:
            raise ValueError("Call cannot be rejected in its current state.")
        if user != call.receiver:
            raise ValueError("Only the receiver can reject the call.")
            
        call.status = CallStatus.REJECTED
        call.ended_at = timezone.now()
        call.save()
        
        CallingService._notify_chat(call.conversation, "call_rejected", {
            "call_id": str(call.call_session_uuid)
        })
        return call

    @staticmethod
    def end_call(call: CallSession, user):
        if call.status != CallStatus.ACCEPTED:
            raise ValueError("Only accepted calls can be ended.")
            
        call.status = CallStatus.ENDED
        call.ended_at = timezone.now()
        
        if call.answered_at:
            delta = call.ended_at - call.answered_at
            call.duration_seconds = int(delta.total_seconds())
            
        call.save()
        
        CallingService._notify_chat(call.conversation, "call_ended", {
            "call_id": str(call.call_session_uuid),
            "duration": call.duration_seconds
        })
        return call

    @staticmethod
    def cancel_call(call: CallSession, user):
        if call.status not in [CallStatus.INITIATED, CallStatus.RINGING]:
            raise ValueError("Call cannot be cancelled in its current state.")
        if user != call.caller:
            raise ValueError("Only the caller can cancel the call.")
            
        call.status = CallStatus.CANCELLED
        call.ended_at = timezone.now()
        call.save()
        
        CallingService._notify_chat(call.conversation, "call_cancelled", {
            "call_id": str(call.call_session_uuid)
        })
        return call
