from django.contrib import admin
from fix_coins.models import FixCoinSettings, FixCoinTransaction, FixCoinWallet


@admin.register(FixCoinSettings)
class FixCoinSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "coins_per_rupee",
        "signup_bonus_coins",
        "reward_coins_per_100_rupees",
        "minimum_redemption_coins",
        "maximum_redemption_percentage",
        "expiry_days",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active",)
    readonly_fields = ("created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting the active settings singleton
        if obj and obj.is_active:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(FixCoinWallet)
class FixCoinWalletAdmin(admin.ModelAdmin):
    list_display = (
        "wallet_uuid",
        "user",
        "available_coins",
        "lifetime_earned_coins",
        "lifetime_redeemed_coins",
        "lifetime_expired_coins",
        "updated_at",
    )
    search_fields = (
        "wallet_uuid",
        "user__email",
        "user__phone",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = (
        "wallet_uuid",
        "user",
        "available_coins",
        "lifetime_earned_coins",
        "lifetime_redeemed_coins",
        "lifetime_expired_coins",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        # Wallets are created via service or user lifecycle
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FixCoinTransaction)
class FixCoinTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_uuid",
        "wallet",
        "transaction_type",
        "coins",
        "balance_before",
        "balance_after",
        "reference_type",
        "reference_id",
        "created_at",
    )
    list_filter = ("transaction_type", "reference_type", "created_at")
    search_fields = (
        "transaction_uuid",
        "wallet__wallet_uuid",
        "wallet__user__email",
        "wallet__user__phone",
        "reference_id",
    )
    readonly_fields = [f.name for f in FixCoinTransaction._meta.fields]

    def has_add_permission(self, request):
        # Transactions are append-only audit logs created by services
        return False

    def has_change_permission(self, request, obj=None):
        # Strictly immutable audit ledger
        return False

    def has_delete_permission(self, request, obj=None):
        return False
