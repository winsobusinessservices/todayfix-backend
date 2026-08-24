from rest_framework import status
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    CreateAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Q

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
)

from business.models import BusinessProfile
from services.models import Service, ServiceEmployee
from services.permissions import (
    IsApprovedBusiness,
    IsServiceOwner,
)

from accounts.choices import UserRole

from .serializers import (
    ServiceReadSerializer,
    ServiceCreateSerializer,
    ServiceUpdateSerializer,
    ServiceEmployeeSerializer,
    ServiceEmployeeReadSerializer,
)


# =============================================================
# LIST SERVICES (public)
# =============================================================

@extend_schema(
    auth=[],
    tags=["Services"],
    summary="List Active Services",
    description=(
        "List all active services. "
        "Accessible without authentication."
    ),
    responses={200: ServiceReadSerializer(many=True)},
)

class ServiceListAPIView(ListAPIView):

    serializer_class = ServiceReadSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = (
            Service.objects
            .select_related(
                "business",
                "category",
                "subcategory",
            )
        )

        # Admins can see both active and inactive services
        if (
            self.request.user.is_authenticated
            and getattr(self.request.user, "role", None)
            == UserRole.ADMIN
        ):
            return qs

        # Everyone else can see only active services
        return qs.filter(is_active=True)


# =============================================================
# RETRIEVE SERVICE (public)
# =============================================================

@extend_schema(
    auth=[],
    tags=["Services"],
    summary="Service Detail",
    description="Retrieve a single service by UUID.",
    responses={200: ServiceReadSerializer},
)
class ServiceDetailAPIView(RetrieveAPIView):

    serializer_class = ServiceReadSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    lookup_field = "service_uuid"

    def get_queryset(self):
        return (
            Service.objects
            .select_related(
                "business",
                "category",
                "subcategory",
            )
        )


# =============================================================
# CREATE SERVICE (business owner)
# =============================================================

@extend_schema(
    tags=["Services"],
    summary="Create Service",
    description=(
        "Create a new service. Only approved "
        "business owners can create services."
    ),
    request=ServiceCreateSerializer,
    responses={201: ServiceReadSerializer},
)
class ServiceCreateAPIView(CreateAPIView):

    serializer_class = ServiceCreateSerializer
    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
    ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        # Derive business from authenticated user
        business = BusinessProfile.objects.filter(
            owner=request.user,
            is_active=True,
        ).first()

        if not business:
            return Response(
                {
                    "success": False,
                    "message": (
                        "No active business profile found."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        service = serializer.save(
            business=business,
        )

        response_serializer = ServiceReadSerializer(
            service,
        )

        return Response(
            {
                "success": True,
                "message": "Service created successfully.",
                "data": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


# =============================================================
# UPDATE SERVICE (business owner)
# =============================================================

@extend_schema(
    tags=["Services"],
    summary="Update Service",
    description=(
        "Update an existing service. Only the "
        "business owner can update their services."
    ),
    request=ServiceUpdateSerializer,
    responses={200: ServiceReadSerializer},
)
class ServiceUpdateAPIView(UpdateAPIView):

    serializer_class = ServiceUpdateSerializer
    permission_classes = [
        IsAuthenticated,
        IsServiceOwner,
    ]
    lookup_field = "service_uuid"
    http_method_names = ["patch"]

    def get_queryset(self):
        return Service.objects.select_related(
            "business",
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        service = serializer.save()

        response_serializer = ServiceReadSerializer(
            service,
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Service updated successfully."
                ),
                "data": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# =============================================================
# DELETE / DEACTIVATE SERVICE (business owner)
# =============================================================

@extend_schema(
    tags=["Services"],
    summary="Delete Service",
    description=(
        "Deactivate a service. Only the "
        "business owner can deactivate their services."
    ),
)
class ServiceDeleteAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsServiceOwner,
    ]

    def get_object(self):
        from django.shortcuts import get_object_or_404

        obj = get_object_or_404(
            Service,
            service_uuid=self.kwargs["service_uuid"],
        )
        self.check_object_permissions(
            self.request, obj
        )
        return obj

    def delete(self, request, service_uuid):
        service = self.get_object()
        service.is_active = False
        service.save(update_fields=["is_active"])

        return Response(
            {
                "success": True,
                "message": (
                    "Service deactivated successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )


# =============================================================
# SEARCH / FILTER SERVICES (public)
# =============================================================

@extend_schema(
    auth=[],
    tags=["Services"],
    summary="Search Services",
    description=(
        "Search and filter services by category, "
        "subcategory, business, price range, "
        "active status, and keyword."
    ),
    parameters=[
        OpenApiParameter(
            name="category",
            description="Category UUID",
            type=str,
            required=False,
        ),

        OpenApiParameter(
            name="category_slug",
            description="Category slug",
            type=str,
            required=False,
        ),

        OpenApiParameter(
            name="subcategory",
            description="Subcategory UUID",
            type=str,
            required=False,
        ),
        OpenApiParameter(
            name="subcategory_slug",
            description="Subcategory slug",
            type=str,
            required=False,
        ),
        OpenApiParameter(
            name="business",
            description="Business UUID",
            type=str,
            required=False,
        ),
        OpenApiParameter(
            name="min_price",
            description="Minimum price",
            type=float,
            required=False,
        ),
        OpenApiParameter(
            name="max_price",
            description="Maximum price",
            type=float,
            required=False,
        ),
        OpenApiParameter(
            name="is_active",
            description="Active status",
            type=bool,
            required=False,
        ),
        OpenApiParameter(
            name="search",
            description="Keyword search (name/description)",
            type=str,
            required=False,
        ),
    ],
    responses={200: ServiceReadSerializer(many=True)},
)
class ServiceSearchAPIView(ListAPIView):

    serializer_class = ServiceReadSerializer
    permission_classes = [AllowAny]
    

    def get_queryset(self):
        qs = (
            Service.objects
            .select_related(
                "business",
                "category",
                "subcategory",
            )
        )

        # Admins can see both active and inactive services
        if not (
            self.request.user.is_authenticated
            and getattr(
                self.request.user,
                "role",
                None,
            ) == UserRole.ADMIN
        ):
            qs = qs.filter(is_active=True)

        params = self.request.query_params

        # Category
        category = params.get("category")
        if category:
            qs = qs.filter(
                category__cat_uuid=category,
            )

        category_slug = params.get("category_slug")
        if category_slug:
            qs = qs.filter(
                category__slug=category_slug,
            )

        # Subcategory
        subcategory = params.get("subcategory")
        if subcategory:
            qs = qs.filter(
                subcategory__subCat_uuid=subcategory,
            )

        subcategory_slug = params.get("subcategory_slug")
        if subcategory_slug:
            qs = qs.filter(
                subcategory__slug=subcategory_slug,
            )

        # Business
        business = params.get("business")
        if business:
            qs = qs.filter(
                business__business_profile_uuid=business,
            )

        # Price range
        min_price = params.get("min_price")
        if min_price:
            qs = qs.filter(
                price__gte=min_price,
            )

        max_price = params.get("max_price")
        if max_price:
            qs = qs.filter(
                price__lte=max_price,
            )

        # Active status filter
        is_active = params.get("is_active")

        if is_active is not None:
            if is_active.lower() == "true":
                qs = qs.filter(is_active=True)

            elif (
                is_active.lower() == "false"
                and self.request.user.is_authenticated
                and getattr(
                    self.request.user,
                    "role",
                    None,
                ) == UserRole.ADMIN
            ):
                qs = qs.filter(is_active=False)
        

        # Keyword search
        search = params.get("search")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
            )

        return qs

# =============================================================
# ASSIGN EMPLOYEE TO SERVICE
# =============================================================

@extend_schema(
    tags=["Services"],
    summary="Assign Employee to Service",
    description=(
        "Assign an employee to a service. "
        "Only the owner of the service can assign employees."
    ),
    request=ServiceEmployeeSerializer,
    responses={201: ServiceEmployeeSerializer},
)
class ServiceEmployeeCreateAPIView(CreateAPIView):

    serializer_class = ServiceEmployeeSerializer

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
    ]

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        service = serializer.validated_data["service"]
        employee = serializer.validated_data["employee"]

        # Service must belong to the logged-in owner
        if service.business.owner_id != request.user.id:
            return Response(
                {
                    "success": False,
                    "message": (
                        "You can only assign employees "
                        "to your own services."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        assignment = ServiceEmployee.objects.create(
            service=service,
            employee=employee,
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Employee assigned to service successfully."
                ),
                "data": {
                    "service_employee_uuid": (
                        str(assignment.service_employee_uuid)
                    ),
                    "service_uuid": (
                        str(service.service_uuid)
                    ),
                    "employee_uuid": (
                        str(employee.employee_uuid)
                    ),
                },
            },
            status=status.HTTP_201_CREATED,
        )

# =============================================================
# LIST EMPLOYEES ASSIGNED TO SERVICE
# =============================================================

@extend_schema(
    tags=["Services"],
    summary="List Employees Assigned to Service",
    description="List employees assigned to a specific service.",
    responses={200: ServiceEmployeeReadSerializer(many=True)},
)
class ServiceEmployeeListAPIView(ListAPIView):

    serializer_class = ServiceEmployeeReadSerializer
    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
    ]

    def get_queryset(self):
        service_uuid = self.kwargs["service_uuid"]

        return ServiceEmployee.objects.filter(
            service__service_uuid=service_uuid,
            service__business__owner=self.request.user,
        ).select_related(
            "employee",
            "service",
        )
