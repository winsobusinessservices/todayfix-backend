from rest_framework import serializers


from ..choices import BusinessType
from ..models import BusinessProfile, BusinessUpgradeRequest, ManagedBusiness


class BusinessUpgradeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessUpgradeRequest
        fields = ("id", "reason", "status", "created_at", "reviewed_at", "rejection_reason")
        read_only_fields = ("id", "status", "created_at", "reviewed_at", "rejection_reason")


class BusinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = (
            "id",
            "owner",
            "business_type",
            "name",
            "description",
            "email",
            "phone",
            "website",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "owner", "created_at")

    def validate_business_type(self, value):
        if value not in BusinessType.values:
            raise serializers.ValidationError("Invalid business type.")
        return value


class ManagedBusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagedBusiness
        fields = ("id", "manager_business", "linked_business", "created_at")
        read_only_fields = ("id", "manager_business", "created_at")


class RejectUpgradeSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
