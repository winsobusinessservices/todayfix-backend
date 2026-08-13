from rest_framework import serializers

from ..models import Category, SubCategory


class SubCategorySerializer(serializers.ModelSerializer):

    category_uuid = serializers.UUIDField(
        source="category.uuid",
        read_only=True,
    )

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    class Meta:
        model = SubCategory

        fields = (
            "uuid",
            "category_uuid",
            "category_name",
            "name",
            "slug",
            "description",
            "icon",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "uuid",
            "category_uuid",
            "category_name",
            "created_at",
            "updated_at",
        )

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Subcategory name is required."
            )

        return value


class CategorySerializer(serializers.ModelSerializer):

    subcategories = SubCategorySerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Category

        fields = (
            "uuid",
            "name",
            "slug",
            "description",
            "icon",
            "is_active",
            "subcategories",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "uuid",
            "subcategories",
            "created_at",
            "updated_at",
        )

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Category name is required."
            )

        return value

        