import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_uuid = self.scope['url_route']['kwargs']['conversation_uuid']
        self.group_name = f"chat_{self.conversation_uuid}"
        
        # In a real app we'd verify the token via middleware or here.
        # Assuming JWT auth middleware handles self.scope['user']
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return
            
        has_access = await self.verify_access(user, self.conversation_uuid)
        if not has_access:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # We can handle custom actions like typing_started etc.
        data = json.loads(text_data)
        event_type = data.get('type')
        
        if event_type in ['typing_started', 'typing_stopped']:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'typing_event',
                    'event_type': event_type,
                    'user_uuid': str(self.scope['user'].user_uuid)
                }
            )

    async def typing_event(self, event):
        await self.send(text_data=json.dumps({
            'type': event['event_type'],
            'user_uuid': event['user_uuid']
        }))

    async def chat_message(self, event):
        # Triggered when a new message is saved (e.g. from signals or views)
        await self.send(text_data=json.dumps(event['message']))

    async def call_event(self, event):
        # Triggered from calling_service
        await self.send(text_data=json.dumps({
            'type': event['event_type'],
            'call_data': event['call_data']
        }))

    @database_sync_to_async
    def verify_access(self, user, conversation_uuid):
        try:
            conv = Conversation.objects.get(conversation_uuid=conversation_uuid)
            if user == conv.customer:
                return True
            if conv.employee and getattr(user, 'employee_profile', None) == conv.employee:
                return True
            if user == conv.business.owner:
                return True
        except Conversation.DoesNotExist:
            pass
        return False
