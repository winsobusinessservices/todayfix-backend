from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "conversation_uuid",
        "booking_type",
        "customer",
        "business",
        "employee",
        "status",
        "closed_at",
        "archived_at",
    )

    list_filter = (
        "booking_type",
        "status",
    )

    search_fields = (
        "conversation_uuid",
        "customer__email",
        "business__name",
        "employee__name",
    )

    readonly_fields = (
        "conversation_uuid",
        "created_at",
        "updated_at",
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "message_uuid",
        "conversation",
        "sender",
        "message_type",
        "is_read",
        "read_at",
        "created_at",
    )

    list_filter = (
        "message_type",
        "is_read",
    )

    search_fields = (
        "message_uuid",
        "conversation__conversation_uuid",
        "sender__email",
        "text",
    )

    readonly_fields = (
        "message_uuid",
        "created_at",
        "updated_at",
    )