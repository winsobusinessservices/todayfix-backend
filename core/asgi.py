import os
from django.core.asgi import get_asgi_application

# 1. Set the settings module FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# 2. Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# 3. NOW you can safely import Channels and your chat routing
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat_service.routing

# 4. Define the application router
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat_service.routing.websocket_urlpatterns
        )
    ),
})

