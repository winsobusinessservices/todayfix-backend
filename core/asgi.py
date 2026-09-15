import os
from django.core.asgi import get_asgi_application

# 1. Set the settings module FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# 2. Initialize Django ASGI application early
django_asgi_app = get_asgi_application()

# 3. Import Channels, your custom JWT middleware, and routing
from channels.routing import ProtocolTypeRouter, URLRouter
from notifications.middleware import JWTAuthMiddleware  # <-- Added this
import chat_service.routing

# 4. Define the application router
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(  # <-- Changed from AuthMiddlewareStack
        URLRouter(
            chat_service.routing.websocket_urlpatterns
        )
    ),
})
