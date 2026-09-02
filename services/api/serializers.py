from rest_framework import serializers

from categories.models import Category, SubCategory

from services.models import Service, ServiceEmployee, ServiceType, Unit
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


class ServiceTypeLiteSerializer(serializers.ModelSerializer):
    """Lightweight service type info for service responses."""

    class Meta:
        model = ServiceType
        fields = ("type_uuid", "name")


class ServiceUnitSerializer(serializers.ModelSerializer):
    """Lightweight unit info for service responses."""

    class Meta:
        model = Unit
        fields = ("unit_uuid", "name")


# =============================================================
# SERVICE TYPE / UNIT ADMIN CRUD
# =============================================================

class UnitSerializer(serializers.ModelSerializer):
    """Admin CRUD serializer for units."""

    type_uuid = serializers.UUIDField(
        source="service_type.type_uuid",
        read_only=True,
    )

    class Meta:
        model = Unit
        fields = (
            "unit_uuid",
            "type_uuid",
            "name",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "unit_uuid",
            "type_uuid",
            "created_at",
            "updated_at",
        )

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Unit name is required."
            )
        return value


class ServiceTypeSerializer(serializers.ModelSerializer):
    """Admin CRUD serializer for service types."""

    units = UnitSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = ServiceType
        fields = (
            "type_uuid",
            "name",
            "slug",
            "is_active",
            "units",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "type_uuid",
            "units",
            "created_at",
            "updated_at",
        )

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Service type name is required."
            )
        return value


# =============================================================
# SERVICE LIST / DETAIL
# =============================================================

class ServiceReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for service responses."""

    business = ServiceBusinessSerializer(read_only=True)
    category = ServiceCategorySerializer(read_only=True)
    subcategory = ServiceSubCategorySerializer(read_only=True)
    service_type = ServiceTypeLiteSerializer(read_only=True)
    unit = ServiceUnitSerializer(read_only=True)

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
            "service_type",
            "unit",
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

    type_uuid = serializers.UUIDField(
        write_only=True,
    )

    unit_uuid = serializers.UUIDField(
        write_only=True,
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
            "type_uuid",
            "unit_uuid",
            "is_active",
        )

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than 0."
            )
        return value

    def validate_type_uuid(self, value):
        try:
            service_type = ServiceType.objects.get(
                type_uuid=value,
                is_active=True,
            )
        except ServiceType.DoesNotExist:
            raise serializers.ValidationError(
                "Service type not found."
            )
        self._service_type = service_type
        return value

    def validate_unit_uuid(self, value):
        try:
            unit = Unit.objects.get(
                unit_uuid=value,
                is_active=True,
            )
        except Unit.DoesNotExist:
            raise serializers.ValidationError(
                "Unit not found."
            )
        self._unit = unit
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

        # Validate unit belongs to service type
        service_type = getattr(self, "_service_type", None)
        unit = getattr(self, "_unit", None)

        if (
            service_type
            and unit
            and unit.service_type_id != service_type.id
        ):
            raise serializers.ValidationError({
                "unit_uuid": (
                    "Unit does not belong to the "
                    "selected service type."
                )
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop("cat_uuid")
        validated_data.pop(
            "subCat_uuid", None
        )
        validated_data.pop("type_uuid")
        validated_data.pop("unit_uuid")

        validated_data["category"] = self._category
        validated_data["subcategory"] = getattr(
            self, "_subcategory", None
        )
        validated_data["service_type"] = self._service_type
        validated_data["unit"] = self._unit

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

    type_uuid = serializers.UUIDField(
        write_only=True,
        required=False,
    )

    unit_uuid = serializers.UUIDField(
        write_only=True,
        required=False,
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
            "type_uuid",
            "unit_uuid",
            "is_active",
        )

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than 0."
            )
        return value

    def validate_type_uuid(self, value):
        try:
            service_type = ServiceType.objects.get(
                type_uuid=value,
                is_active=True,
            )
        except ServiceType.DoesNotExist:
            raise serializers.ValidationError(
                "Service type not found."
            )
        self._service_type = service_type
        return value

    def validate_unit_uuid(self, value):
        try:
            unit = Unit.objects.get(
                unit_uuid=value,
                is_active=True,
            )
        except Unit.DoesNotExist:
            raise serializers.ValidationError(
                "Unit not found."
            )
        self._unit = unit
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

        # Validate unit belongs to service type.
        # Falls back to the instance's current value
        # when only one of the two is being changed.
        instance = getattr(self, "instance", None)

        service_type = getattr(
            self,
            "_service_type",
            instance.service_type if instance else None,
        )

        unit = getattr(
            self,
            "_unit",
            instance.unit if instance else None,
        )

        if (
            service_type
            and unit
            and unit.service_type_id != service_type.id
        ):
            raise serializers.ValidationError({
                "unit_uuid": (
                    "Unit does not belong to the "
                    "selected service type."
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

        if "type_uuid" in validated_data:
            validated_data.pop("type_uuid")
            instance.service_type = self._service_type

        if "unit_uuid" in validated_data:
            validated_data.pop("unit_uuid")
            instance.unit = self._unit

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

class MyServiceReadSerializer(serializers.ModelSerializer):
    """Services belonging to the logged-in business owner."""

    business = ServiceBusinessSerializer(read_only=True)
    category = ServiceCategorySerializer(read_only=True)
    subcategory = ServiceSubCategorySerializer(read_only=True)
    service_type = ServiceTypeLiteSerializer(read_only=True)
    unit = ServiceUnitSerializer(read_only=True)

    employees = ServiceEmployeeReadSerializer(
        source="employee_assignments",
        many=True,
        read_only=True,
    )

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
            "service_type",
            "unit",
            "employees",
            "is_active",
            "created_at",
            "updated_at",
        )