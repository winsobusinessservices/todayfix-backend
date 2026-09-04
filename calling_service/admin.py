from django.contrib import admin

from .models import CallSession


@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = (
        "call_session_uuid",
        "conversation",
        "caller",
        "receiver",
        "call_type",
        "status",
        "started_at",
        "ended_at",
        "duration_seconds",
    )

    list_filter = (
        "call_type",
        "status",
    )

    search_fields = (
        "call_session_uuid",
        "caller__email",
        "receiver__email",
        "provider_call_id",
    )

    readonly_fields = (
        "call_session_uuid",
        "created_at",
        "updated_at",
    )