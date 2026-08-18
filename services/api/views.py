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
from services.models import Service
from services.permissions import (
    IsApprovedBusiness,
    IsServiceOwner,
)

from .serializers import (
    ServiceReadSerializer,
    ServiceCreateSerializer,
    ServiceUpdateSerializer,
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
    authentication_classes = []

    def get_queryset(self):
        return (
            Service.objects
            .filter(is_active=True)
            .select_related(
                "business",
                "category",
                "subcategory",
            )
        )


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
            name="subcategory",
            description="Subcategory UUID",
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
    authentication_classes = []

    def get_queryset(self):
        qs = (
            Service.objects
            .select_related(
                "business",
                "category",
                "subcategory",
            )
            .filter(is_active=True)
        )

        params = self.request.query_params

        # Category
        category = params.get("category")
        if category:
            qs = qs.filter(
                category__cat_uuid=category,
            )

        # Subcategory
        subcategory = params.get("subcategory")
        if subcategory:
            qs = qs.filter(
                subcategory__subCat_uuid=subcategory,
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

        # Active status override
        is_active = params.get("is_active")
        if is_active is not None:
            if is_active.lower() == "false":
                qs = Service.objects.filter(
                    is_active=False,
                )

        # Keyword search
        search = params.get("search")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
            )

        return qs
