from rest_framework import serializers

from services.models import Service
from business.models import BusinessProfile
from categories.models import Category, SubCategory


# =============================================================
# NESTED READ SERIALIZERS
# =============================================================

class ServiceBusinessSerializer(serializers.ModelSerializer):
    """Lightweight business info for service responses."""

    class Meta:
        model = BusinessProfile
        fields = ("uuid", "name")


class ServiceCategorySerializer(serializers.ModelSerializer):
    """Lightweight category info for service responses."""

    class Meta:
        model = Category
        fields = ("uuid", "name")


class ServiceSubCategorySerializer(serializers.ModelSerializer):
    """Lightweight subcategory info for service responses."""

    class Meta:
        model = SubCategory
        fields = ("uuid", "name")


# =============================================================
# SERVICE LIST / DETAIL
# =============================================================

class ServiceReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for service responses."""

    business = ServiceBusinessSerializer(read_only=True)
    category = ServiceCategorySerializer(read_only=True)
    subcategory = ServiceSubCategorySerializer(read_only=True)

    class Meta:
        model = Service
        fields = (
            "uuid",
            "name",
            "description",
            "price",
            "duration",
            "business",
            "category",
            "subcategory",
            "is_active",
            "created_at",
            "updated_at",
        )


# =============================================================
# SERVICE CREATE
# =============================================================

class ServiceCreateSerializer(serializers.ModelSerializer):
    """
    Create serializer for services.

    Business is derived from request.user, not sent
    by the client.
    """

    category_uuid = serializers.UUIDField(
        write_only=True,
    )

    subcategory_uuid = serializers.UUIDField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Service
        fields = (
            "name",
            "description",
            "price",
            "duration",
            "category_uuid",
            "subcategory_uuid",
            "is_active",
        )

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than 0."
            )
        return value

    def validate_category_uuid(self, value):
        try:
            category = Category.objects.get(
                uuid=value,
                is_active=True,
            )
        except Category.DoesNotExist:
            raise serializers.ValidationError(
                "Category not found."
            )
        self._category = category
        return value

    def validate_subcategory_uuid(self, value):
        if value is None:
            return value

        try:
            subcategory = SubCategory.objects.get(
                uuid=value,
                is_active=True,
            )
        except SubCategory.DoesNotExist:
            raise serializers.ValidationError(
                "Subcategory not found."
            )
        self._subcategory = subcategory
        return value

    def validate(self, attrs):
        # Validate subcategory belongs to category
        subcategory = getattr(
            self, "_subcategory", None
        )
        category = getattr(
            self, "_category", None
        )

        if (
            subcategory
            and category
            and subcategory.category != category
        ):
            raise serializers.ValidationError({
                "subcategory_uuid": (
                    "Subcategory does not belong "
                    "to the selected category."
                )
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop("category_uuid")
        validated_data.pop(
            "subcategory_uuid", None
        )

        validated_data["category"] = self._category
        validated_data["subcategory"] = getattr(
            self, "_subcategory", None
        )

        return super().create(validated_data)


# =============================================================
# SERVICE UPDATE
# =============================================================

class ServiceUpdateSerializer(serializers.ModelSerializer):
    """Partial update serializer for services."""

    category_uuid = serializers.UUIDField(
        write_only=True,
        required=False,
    )

    subcategory_uuid = serializers.UUIDField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Service
        fields = (
            "name",
            "description",
            "price",
            "duration",
            "category_uuid",
            "subcategory_uuid",
            "is_active",
        )

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than 0."
            )
        return value

    def validate_category_uuid(self, value):
        try:
            category = Category.objects.get(
                uuid=value,
                is_active=True,
            )
        except Category.DoesNotExist:
            raise serializers.ValidationError(
                "Category not found."
            )
        self._category = category
        return value

    def validate_subcategory_uuid(self, value):
        if value is None:
            self._subcategory = None
            return value

        try:
            subcategory = SubCategory.objects.get(
                uuid=value,
                is_active=True,
            )
        except SubCategory.DoesNotExist:
            raise serializers.ValidationError(
                "Subcategory not found."
            )
        self._subcategory = subcategory
        return value

    def update(self, instance, validated_data):
        if "category_uuid" in validated_data:
            validated_data.pop("category_uuid")
            instance.category = self._category

        if "subcategory_uuid" in validated_data:
            validated_data.pop("subcategory_uuid")
            instance.subcategory = getattr(
                self, "_subcategory", None
            )

        return super().update(
            instance, validated_data
        )
