from rest_framework import serializers

from categories.models import Category, SubCategory

from services.models import Service, ServiceEmployee
from business.models import BusinessProfile, Employee

from business.choices import BusinessType


# =============================================================
# NESTED READ SERIALIZERS
# =============================================================

class ServiceBusinessSerializer(serializers.ModelSerializer):
    """Lightweight business info for service responses."""

    class Meta:
        model = BusinessProfile
        fields = ("business_profile_uuid", "name")


class ServiceCategorySerializer(serializers.ModelSerializer):
    """Lightweight category info for service responses."""

    class Meta:
        model = Category
        fields = ("cat_uuid", "name")


class ServiceSubCategorySerializer(serializers.ModelSerializer):
    """Lightweight subcategory info for service responses."""

    class Meta:
        model = SubCategory
        fields = ("subCat_uuid", "name")


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
            "service_uuid",
            "name",
            "description",
            "price",
            "duration",
            "required_employees",
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

    cat_uuid = serializers.UUIDField(
        write_only=True,
    )

    subCat_uuid = serializers.UUIDField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    required_employees = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    class Meta:
        model = Service
        fields = (
            "name",
            "description",
            "price",
            "duration",
            "required_employees",
            "cat_uuid",
            "subCat_uuid",
            "is_active",
        )

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than 0."
            )
        return value


    def validate_cat_uuid(self, value):
        try:
            category = Category.objects.get(
                cat_uuid=value,
                is_active=True,
            )
        except Category.DoesNotExist:
            raise serializers.ValidationError(
                "Category not found."
            )
        self._category = category
        return value

    def validate_subCat_uuid(self, value):
        if value is None:
            return value

        try:
            subcategory = SubCategory.objects.get(
                subCat_uuid=value,
                is_active=True,
            )
        except SubCategory.DoesNotExist:
            raise serializers.ValidationError(
                "Subcategory not found."
            )
        self._subcategory = subcategory
        return value

    def validate(self, attrs):
        request = self.context.get("request")

        business = BusinessProfile.objects.filter(
            owner=request.user,
            is_active=True,
        ).first()

        if not business:
            raise serializers.ValidationError(
                "No active business profile found."
            )

        # Individual business → always 1 employee
        if business.business_type == BusinessType.INDIVIDUAL:
            if "required_employees" in attrs:
                raise serializers.ValidationError({
                    "required_employees": (
                        "Required employees are not available "
                        "for Individual businesses. Please upgrade "
                        "to a Company or Investor business to use "
                        "multiple employees for a service."
                    )
                })

            attrs["required_employees"] = 1

        elif business.business_type in [
            BusinessType.COMPANY,
            BusinessType.INVESTOR,
        ]:
            if "required_employees" not in attrs:
                raise serializers.ValidationError({
                    "required_employees": (
                        "This field is required for "
                        "Company and Investor businesses."
                    )
                })

        # Validate subcategory belongs to category
        subcategory = getattr(
            self,
            "_subcategory",
            None,
        )

        category = getattr(
            self,
            "_category",
            None,
        )

        if (
            subcategory
            and category
            and subcategory.category != category
        ):
            raise serializers.ValidationError({
                "subCat_uuid": (
                    "Subcategory does not belong "
                    "to the selected category."
                )
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop("cat_uuid")
        validated_data.pop(
            "subCat_uuid", None
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

    cat_uuid = serializers.UUIDField(
        write_only=True,
        required=False,
    )

    subCat_uuid = serializers.UUIDField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    required_employees = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    class Meta:
        model = Service
        fields = (
            "name",
            "description",
            "price",
            "duration",
            "required_employees",
            "cat_uuid",
            "subCat_uuid",
            "is_active",
        )

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than 0."
            )
        return value

    def validate_required_employees(self, value):
        request = self.context.get("request")

        business = BusinessProfile.objects.filter(
            owner=request.user,
            is_active=True,
        ).first()

        if not business:
            raise serializers.ValidationError(
                "No active business profile found."
            )

        if business.business_type == BusinessType.INDIVIDUAL:
            raise serializers.ValidationError({
                "required_employees": (
                    "Required employees are not available "
                    "for Individual businesses. Please upgrade "
                    "to a Company or Investor business to use "
                    "multiple employees for a service."
                )
            })

        return value

    def validate_cat_uuid(self, value):
        try:
            category = Category.objects.get(
                cat_uuid=value,
                is_active=True,
            )
        except Category.DoesNotExist:
            raise serializers.ValidationError(
                "Category not found."
            )

        self._category = category
        return value

    def validate_subCat_uuid(self, value):
        if value is None:
            self._subcategory = None
            return value

        try:
            subcategory = SubCategory.objects.get(
                subCat_uuid=value,
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
            self,
            "_subcategory",
            None,
        )

        category = getattr(
            self,
            "_category",
            None,
        )

        if (
            subcategory
            and category
            and subcategory.category != category
        ):
            raise serializers.ValidationError({
                "subCat_uuid": (
                    "Subcategory does not belong "
                    "to the selected category."
                )
            })

        return attrs

    def update(self, instance, validated_data):
        if "cat_uuid" in validated_data:
            validated_data.pop("cat_uuid")
            instance.category = self._category

        if "subCat_uuid" in validated_data:
            validated_data.pop("subCat_uuid")
            instance.subcategory = getattr(
                self,
                "_subcategory",
                None,
            )

        return super().update(
            instance,
            validated_data,
        )
# =============================================================
# SERVICE - EMPLOYEE ASSIGNMENT
# =============================================================

class ServiceEmployeeSerializer(serializers.ModelSerializer):
    """
    Assigns an employee to a service.
    The employee must belong to the same business as the service.
    """

    service_uuid = serializers.UUIDField(
        write_only=True,
    )

    employee_uuid = serializers.UUIDField(
        write_only=True,
    )

    class Meta:
        model = ServiceEmployee
        fields = (
            "service_uuid",
            "employee_uuid",
        )

    def validate(self, attrs):
        service_uuid = attrs.pop("service_uuid")
        employee_uuid = attrs.pop("employee_uuid")

        try:
            service = Service.objects.get(
                service_uuid=service_uuid,
                is_active=True,
            )
        except Service.DoesNotExist:
            raise serializers.ValidationError({
                "service_uuid": "Service not found."
            })

        try:
            employee = Employee.objects.get(
                employee_uuid=employee_uuid,
                is_active=True,
            )
        except Employee.DoesNotExist:
            raise serializers.ValidationError({
                "employee_uuid": "Employee not found."
            })

        # Employee must belong to the same business
        if employee.business_id != service.business_id:
            raise serializers.ValidationError({
                "employee_uuid": (
                    "Employee does not belong to the "
                    "service's business."
                )
            })

        attrs["service"] = service
        attrs["employee"] = employee

        return attrs

class ServiceEmployeeReadSerializer(serializers.ModelSerializer):

    service_uuid = serializers.UUIDField(
        source="service.service_uuid",
        read_only=True,
    )

    employee_uuid = serializers.UUIDField(
        source="employee.employee_uuid",
        read_only=True,
    )

    employee_name = serializers.CharField(
        source="employee.name",
        read_only=True,
    )

    class Meta:
        model = ServiceEmployee
        fields = (
            "service_uuid",
            "employee_uuid",
            "employee_name",
        )