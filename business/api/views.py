from django.db import transaction
from django.shortcuts import get_object_or_404

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)

from rest_framework import status
from rest_framework.parsers import (
    FormParser,
    JSONParser,
    MultiPartParser,
)

from bookings.models import BookingEmployee 
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.choices import UserRole

from ..choices import BusinessApplicationStatus, BusinessType, EmployeeAvailabilityStatus
from ..models import (
    BusinessApplication,
    BusinessBankAccount,
    BusinessIdentity,
    BusinessProfile,
    Employee,
    ProviderAvailability,
    EmployeeWorkingSchedule,
)
from ..permissions import IsAdminRole, IsApprovedBusiness, IsEmployeeManagementAllowed
from ..services import BusinessApplicationService

from .serializers import (
    BusinessApplicationFullSerializer,
    BusinessApplicationSubmitSerializer,
    BusinessProfileSerializer,
    RejectBusinessApplicationSerializer,
    EmployeeCreateSerializer,
    EmployeeListSerializer,
    EmployeeUpdateSerializer,
    ProviderAvailabilitySerializer,
    EmployeeWorkingScheduleSerializer,
)

from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    CreateAPIView,
    
)

from django.db.models import Q

from django.http import HttpResponse


# =========================================================
# USER
# CREATE BUSINESS APPLICATION
# =========================================================

class BusinessApplicationCreateAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]

    @extend_schema(
        tags=["Business Application"],
        summary="Submit complete business application",
        description=(
            "Only USER accounts can use this API. "
            "All business application information must "
            "be submitted in ONE multipart/form-data request.\n\n"

            "INDIVIDUAL:\n"
            "- PAN OR Aadhaar minimum one complete pair\n"
            "- Bank details mandatory\n\n"

            "COMPANY / INVESTOR:\n"
            "- PAN number + document mandatory\n"
            "- Aadhaar number + document mandatory\n"
            "- At least one of GST/Udyam/Labour/BBMP/Food "
            "registration mandatory\n"
            "- Internal store photo mandatory\n"
            "- External store photo mandatory\n"
            "- Cancelled GST bill/book photo mandatory\n"
            "- Logo optional\n"
            "- Website optional\n"
            "- Bank details mandatory"
        ),
        request=BusinessApplicationSubmitSerializer,
        responses={
            201: BusinessApplicationFullSerializer,
            400: OpenApiResponse(
                description="Validation error"
            ),
            403: OpenApiResponse(
                description="Only USER accounts allowed"
            ),
        },
    )
    def post(self, request):

        # =================================================
        # ROLE CHECK
        # =================================================

        if request.user.role != UserRole.USER:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Only USER accounts can "
                        "submit a business application."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # =================================================
        # VALIDATE EVERYTHING
        # =================================================

        serializer = (
            BusinessApplicationSubmitSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        # =================================================
        # PENDING APPLICATION CHECK
        # =================================================

        if BusinessApplication.objects.filter(
            user=request.user,
            status=(
                BusinessApplicationStatus.PENDING
            ),
        ).exists():

            return Response(
                {
                    "success": False,
                    "message": (
                        "You already have a pending "
                        "business application."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # =================================================
        # CREATE EVERYTHING ATOMICALLY
        # =================================================

        try:

            with transaction.atomic():

                # -----------------------------------------
                # APPLICATION
                # -----------------------------------------

                application = BusinessApplicationService.submit(
                    user=request.user,
                    business_type=data["business_type"],
                    location=data["location"],
                    category=data["category"],
                )

                pan_document = data.get("pan_document")
                aadhaar_document = data.get("aadhaar_document")
                internal_store_photo = data.get("internal_store_photo")
                external_store_photo = data.get("external_store_photo")
                cancelled_gst_bill_book_photo = data.get(
                    "cancelled_gst_bill_book_photo"
                )
                logo = data.get("logo")

                # -----------------------------------------
                # IDENTITY
                # -----------------------------------------

                identity = (
                    BusinessIdentity.objects.create(
                        application=application,

                        pan_number=data.get(
                            "pan_number",
                            "",
                        ),

                        pan_document=(
                            pan_document.read()
                            if pan_document
                            else None
                        ),
                        pan_document_name=(
                            pan_document.name
                            if pan_document
                            else ""
                        ),
                        pan_document_type=(
                            pan_document.content_type
                            if pan_document
                            else ""
                        ),

                        aadhaar_number=data.get(
                            "aadhaar_number",
                            "",
                        ),

                        aadhaar_document=(
                            aadhaar_document.read()
                            if aadhaar_document
                            else None
                        ),
                        aadhaar_document_name=(
                            aadhaar_document.name
                            if aadhaar_document
                            else ""
                        ),
                        aadhaar_document_type=(
                            aadhaar_document.content_type
                            if aadhaar_document
                            else ""
                        ),

                        gst_number=data.get(
                            "gst_number",
                            "",
                        ),

                        udyam_number=data.get(
                            "udyam_number",
                            "",
                        ),

                        labour_license_number=data.get(
                            "labour_license_number",
                            "",
                        ),

                        bbmp_license_number=data.get(
                            "bbmp_license_number",
                            "",
                        ),

                        food_license_number=data.get(
                            "food_license_number",
                            "",
                        ),

                        internal_store_photo=(
                            internal_store_photo.read()
                            if internal_store_photo
                            else None
                        ),
                        internal_store_name=(
                            internal_store_photo.name
                            if internal_store_photo
                            else ""
                        ),
                        internal_store_type=(
                            internal_store_photo.content_type
                            if internal_store_photo
                            else ""
                        ),

                        external_store_photo=(
                            external_store_photo.read()
                            if external_store_photo
                            else None
                        ),
                        external_store_name=(
                            external_store_photo.name
                            if external_store_photo
                            else ""
                        ),
                        external_store_type=(
                            external_store_photo.content_type
                            if external_store_photo
                            else ""
                        ),

                        cancelled_gst_bill_book_photo=(
                            cancelled_gst_bill_book_photo.read()
                            if cancelled_gst_bill_book_photo
                            else None
                        ),
                        cancelled_gst_bill_book_name=(
                            cancelled_gst_bill_book_photo.name
                            if cancelled_gst_bill_book_photo
                            else ""
                        ),
                        cancelled_gst_bill_book_type=(
                            cancelled_gst_bill_book_photo.content_type
                            if cancelled_gst_bill_book_photo
                            else ""
                        ),

                        logo=(
                            logo.read()
                            if logo
                            else None
                        ),
                        logo_name=(
                            logo.name
                            if logo
                            else ""
                        ),
                        logo_type=(
                            logo.content_type
                            if logo
                            else ""
                        ),

                        website=data.get(
                            "website",
                            "",
                        ),
                    )
                )

                # -----------------------------------------
                # BANK ACCOUNT
                # -----------------------------------------

                bank_account = (
                    BusinessBankAccount.objects.create(
                        application=application,

                        account_holder_name=data[
                            "account_holder_name"
                        ],

                        account_number=data[
                            "account_number"
                        ],

                        ifsc_code=data[
                            "ifsc_code"
                        ],

                        bank_name=data[
                            "bank_name"
                        ],

                        branch_name=data.get(
                            "branch_name",
                            "",
                        ),
                    )
                )

                # -----------------------------------------
                # FINAL MODEL VALIDATION
                # -----------------------------------------

                identity.full_clean()

                bank_account.full_clean()

        except ValueError as exc:

            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Business application submitted "
                    "successfully. It is waiting for "
                    "admin review."
                ),
                "data": (
                    BusinessApplicationFullSerializer(
                        application
                    ).data
                ),
            },
            status=status.HTTP_201_CREATED,
        )

#
@extend_schema(
    tags=["Business Administration"],
)
class BusinessApplicationDocumentAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request,
        business_application_uuid,
        document_type,
    ):
        try:
            application = BusinessApplication.objects.get(
                business_application_uuid=business_application_uuid
            )
        except BusinessApplication.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Business application not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if (
            application.user != request.user
            and getattr(request.user, "role", None) != UserRole.ADMIN
        ):
            return Response(
                {
                    "success": False,
                    "message": "You do not have permission to access this document.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            identity = application.identity
        except BusinessIdentity.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Business identity not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        document_map = {
            "pan": (
                identity.pan_document,
                identity.pan_document_name,
                identity.pan_document_type,
            ),
            "aadhaar": (
                identity.aadhaar_document,
                identity.aadhaar_document_name,
                identity.aadhaar_document_type,
            ),
            "internal-store": (
                identity.internal_store_photo,
                identity.internal_store_name,
                identity.internal_store_type,
            ),
            "external-store": (
                identity.external_store_photo,
                identity.external_store_name,
                identity.external_store_type,
            ),
            "cancelled-gst": (
                identity.cancelled_gst_bill_book_photo,
                identity.cancelled_gst_bill_book_name,
                identity.cancelled_gst_bill_book_type,
            ),
            "logo": (
                identity.logo,
                identity.logo_name,
                identity.logo_type,
            ),
        }

        if document_type not in document_map:
            return Response(
                {
                    "success": False,
                    "message": "Invalid document type.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        document, file_name, content_type = document_map[
            document_type
        ]

        if not document:
            return Response(
                {
                    "success": False,
                    "message": "Document not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        response = HttpResponse(
            document,
            content_type=content_type
            or "application/octet-stream",
        )

        response[
            "Content-Disposition"
        ] = f'inline; filename="{file_name}"'

        return response


# =========================================================
# USER
# LIST MY APPLICATIONS
# =========================================================

class BusinessApplicationListAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    @extend_schema(
        tags=["Business Application"],
        summary="List my business applications",
        responses=BusinessApplicationFullSerializer(
            many=True
        ),
    )
    def get(self, request):

        applications = (
            BusinessApplication.objects
            .filter(
                user=request.user
            )
            .select_related(
                "user",
                "reviewed_by",
            )
            .prefetch_related(
                "identity",
                "bank_account",
            )
        )

        serializer = (
            BusinessApplicationFullSerializer(
                applications,
                many=True,
            )
        )

        return Response(
            {
                "success": True,
                "data": serializer.data,
            }
        )


# =========================================================
# USER
# APPLICATION DETAIL
# =========================================================

class BusinessApplicationDetailAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    @extend_schema(
        tags=["Business Application"],
        summary="View my business application",
        responses=BusinessApplicationFullSerializer,
    )
    def get(
        self,
        request,
        business_application_uuid,
    ):

        application = get_object_or_404(
            BusinessApplication.objects
            .select_related(
                "user",
                "reviewed_by",
            )
            .prefetch_related(
                "identity",
                "bank_account",
            ),
            business_application_uuid=business_application_uuid,
            user=request.user,
        )

        serializer = (
            BusinessApplicationFullSerializer(
                application
            )
        )

        return Response(
            {
                "success": True,
                "data": serializer.data,
            }
        )


# =========================================================
# ADMIN
# LIST APPLICATIONS
# =========================================================

class AdminBusinessApplicationListAPIView(APIView):

    permission_classes = [
        IsAdminRole
    ]

    @extend_schema(
        tags=["Business Administration"],
        summary="List business applications",
        responses=BusinessApplicationFullSerializer(
            many=True
        ),
    )
    def get(self, request):

        applications = (
            BusinessApplication.objects
            .select_related(
                "user",
                "reviewed_by",
            )
            .prefetch_related(
                "identity",
                "bank_account",
            )
        )

        status_filter = (
            request.query_params.get(
                "status"
            )
        )

        if status_filter:

            applications = applications.filter(
                status=status_filter.upper()
            )

        serializer = (
            BusinessApplicationFullSerializer(
                applications,
                many=True,
            )
        )

        return Response(
            {
                "success": True,
                "data": serializer.data,
            }
        )


# =========================================================
# ADMIN
# APPROVE
# =========================================================

class AdminApproveBusinessApplicationAPIView(
    APIView
):

    permission_classes = [
        IsAdminRole
    ]

    @extend_schema(
        tags=["Business Administration"],
        summary="Approve business application",
        description=(
            "Approving the application changes the "
            "USER role to BUSINESS and creates the "
            "active BusinessProfile."
        ),
        request=None,
        responses=BusinessApplicationFullSerializer,
    )
    def post(
        self,
        request,
        business_application_uuid,
    ):

        application = get_object_or_404(
            BusinessApplication,
            business_application_uuid=business_application_uuid,
        )

        try:

            application, profile = (
                BusinessApplicationService.approve(
                    application=application,
                    admin_user=request.user,
                )
            )

        except ValueError as exc:

            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Business application approved. "
                    "User role is now BUSINESS."
                ),
                "data": (
                    BusinessApplicationFullSerializer(
                        application
                    ).data
                ),
                "business_profile_uuid": str(
                    profile.business_profile_uuid
                ),
            },
            status=status.HTTP_200_OK,
        )


# =========================================================
# ADMIN
# REJECT
# =========================================================

class AdminRejectBusinessApplicationAPIView(
    APIView
):

    permission_classes = [
        IsAdminRole
    ]

    @extend_schema(
        tags=["Business Administration"],
        summary="Reject business application",
        description=(
            "Admin must provide a rejection reason."
        ),
        request=RejectBusinessApplicationSerializer,
        responses=BusinessApplicationFullSerializer,
    )
    def post(
        self,
        request,
        business_application_uuid,
    ):

        application = get_object_or_404(
            BusinessApplication,
            business_application_uuid=business_application_uuid,
        )

        serializer = (
            RejectBusinessApplicationSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            application = (
                BusinessApplicationService.reject(
                    application=application,
                    admin_user=request.user,
                    reason=serializer.validated_data[
                        "reason"
                    ],
                )
            )

        except ValueError as exc:

            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Business application rejected."
                ),
                "data": (
                    BusinessApplicationFullSerializer(
                        application
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )


# =========================================================
# BUSINESS PROFILE
# =========================================================

class BusinessProfileListAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    @extend_schema(
        tags=["Business Profile"],
        summary="List my business profiles",
        responses=BusinessProfileSerializer(
            many=True
        ),
    )
    def get(self, request):

        profiles = (
            BusinessProfile.objects
            .filter(
                owner=request.user
            )
        )

        serializer = (
            BusinessProfileSerializer(
                profiles,
                many=True,
            )
        )

        return Response(
            {
                "success": True,
                "data": serializer.data,
            }
        )


# =========================================================
# BUSINESS PROFILE UPDATE
# =========================================================

class BusinessProfileUpdateAPIView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    @extend_schema(
        tags=["Business Profile"],
        summary="Update my business profile",
        request=BusinessProfileSerializer,
        responses=BusinessProfileSerializer,
    )
    def patch(
        self,
        request,
        business_profile_uuid,
    ):

        profile = get_object_or_404(
            BusinessProfile,
            business_profile_uuid=business_profile_uuid,
            owner=request.user,
        )

        serializer = (
            BusinessProfileSerializer(
                profile,
                data=request.data,
                partial=True,
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            {
                "success": True,
                "message": (
                    "Business profile updated "
                    "successfully."
                ),
                "data": serializer.data,
            }
        )

#======================================================================================================
#                           Create Employee API
#======================================================================================================

@extend_schema(
    tags=["Business Employees"],
    summary="Create Employee",
    description=(
        "Create an employee record under the "
        "authenticated business."
    ),
    request=EmployeeCreateSerializer,
    responses={201: EmployeeCreateSerializer},
)

class EmployeeCreateAPIView(CreateAPIView):

    
    serializer_class = EmployeeCreateSerializer

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
        IsEmployeeManagementAllowed,
    ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        business = BusinessProfile.objects.filter(
            owner=request.user,
            is_active=True,
        ).first()

        if not business:
            return Response(
                {
                    "success": False,
                    "message": "No active business profile found.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        employee = serializer.save(
            business=business,
        )

        return Response(
            {
                "success": True,
                "message": "Employee created successfully.",
                "data": EmployeeCreateSerializer(
                    employee
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

#=============================================================
#       Employee List API view
#==============================================================
@extend_schema(
    tags=["Business Employees"],
    summary="List Employees",
    description=(
        "List all employees belonging to the "
        "authenticated business."
    ),
    responses={200: EmployeeListSerializer(many=True)},
)
class EmployeeListAPIView(ListAPIView):
    serializer_class = EmployeeListSerializer

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
        IsEmployeeManagementAllowed,
    ]

    def get_queryset(self):
        business = BusinessProfile.objects.filter(
            owner=self.request.user,
            is_active=True,
        ).first()

        if not business:
            return Employee.objects.none()

        return Employee.objects.filter(
            business=business,
            is_active=True,
        ).order_by("-created_at")

#=================================================================
#               Update Employees API View
#=================================================================
@extend_schema(
    tags=["Business Employees"],
    summary="Update Employee",
    request=EmployeeUpdateSerializer,
    responses={200: EmployeeUpdateSerializer},
)
class EmployeeUpdateAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
        IsEmployeeManagementAllowed,
    ]

    def post(self, request, employee_uuid):

        business = BusinessProfile.objects.filter(
            owner=request.user,
            is_active=True,
        ).first()

        if not business:
            return Response(
                {
                    "success": False,
                    "message": "No active business profile found.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        employee = get_object_or_404(
            Employee,
            employee_uuid=employee_uuid,
            business=business,
        )

        serializer = EmployeeUpdateSerializer(
            employee,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "success": True,
                "message": "Employee updated successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


#============================================================================================
#                   Delete Employee API View
#============================================================================================

@extend_schema(
    tags=["Business Employees"],
    summary="Deactivate Employee",
    description=(
        "Deactivate an employee belonging to the "
        "authenticated business."
    ),
    responses={200: OpenApiResponse(
        description="Employee deactivated successfully."
    )},
)
class EmployeeDeleteAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
        IsEmployeeManagementAllowed,
    ]

    def delete(self, request, employee_uuid):

        business = BusinessProfile.objects.filter(
            owner=request.user,
            is_active=True,
        ).first()

        if not business:
            return Response(
                {
                    "success": False,
                    "message": "No active business profile found.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        employee = get_object_or_404(
            Employee,
            employee_uuid=employee_uuid,
            business=business,
        )

        active_assignments = BookingEmployee.objects.filter(
            employee=employee,
            booking__status__in=[
                "PENDING",
                "CONFIRMED",
            ],
        ).exists()

        if active_assignments:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Employee cannot be removed because they "
                        "are currently assigned to a booking. "
                        "Please reassign the booking first."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee.is_active = False
        employee.save(update_fields=["is_active", "updated_at"])

        return Response(
            {
                "success": True,
                "message": "Employee deactivated successfully.",
            },
            status=status.HTTP_200_OK,
        )

# ============================================================
# PROVIDER AVAILABILITY
# ============================================================

@extend_schema(
    tags=["Provider Availability"],
    summary="Create Provider Availability",
    request=ProviderAvailabilitySerializer,
    responses={201: ProviderAvailabilitySerializer},
)
class ProviderAvailabilityCreateAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
    ]

    def post(self, request):

        business = get_object_or_404(
            BusinessProfile,
            owner=request.user,
            is_active=True,
        )

        employee_uuid = request.data.get("employee_uuid")
        status_value = request.data.get(
            "status",
            EmployeeAvailabilityStatus.AVAILABLE,
        )

        # ----------------------------------------------------
        # INDIVIDUAL BUSINESS
        # Owner is the provider
        # ----------------------------------------------------

        if business.business_type == BusinessType.INDIVIDUAL:

            if employee_uuid:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Individual businesses cannot "
                            "set employee availability."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if ProviderAvailability.objects.filter(
                business=business,
                owner=request.user,
            ).exists():
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Provider availability already exists. "
                            "Use the update API."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            availability = ProviderAvailability.objects.create(
                business=business,
                owner=request.user,
                status=status_value,
            )

        # ----------------------------------------------------
        # COMPANY / INVESTOR
        # Employee is the provider
        # ----------------------------------------------------

        else:

            if not employee_uuid:
                return Response(
                    {
                        "success": False,
                        "message": "employee_uuid is required.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            employee = get_object_or_404(
                Employee,
                employee_uuid=employee_uuid,
                business=business,
                is_active=True,
            )

            if ProviderAvailability.objects.filter(
                business=business,
                employee=employee,
            ).exists():
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Provider availability already exists "
                            "for this employee. Use the update API."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            availability = ProviderAvailability.objects.create(
                business=business,
                employee=employee,
                status=status_value,
            )

        serializer = ProviderAvailabilitySerializer(
            availability
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Provider availability created successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# UPDATE PROVIDER AVAILABILITY
# ============================================================

@extend_schema(
    tags=["Provider Availability"],
    summary="Update Provider Availability",
    request=ProviderAvailabilitySerializer,
    responses={200: ProviderAvailabilitySerializer},
)
class ProviderAvailabilityUpdateAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
    ]

    def post(
        self,
        request,
        provider_availability_uuid,
    ):

        business = get_object_or_404(
            BusinessProfile,
            owner=request.user,
            is_active=True,
        )

        availability = get_object_or_404(
            ProviderAvailability,
            provider_availability_uuid=(
                provider_availability_uuid
            ),
            business=business,
        )

        status_value = request.data.get("status")

        if not status_value:
            return Response(
                {
                    "success": False,
                    "message": "status is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if status_value not in dict(
            EmployeeAvailabilityStatus.choices
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Invalid availability status."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        availability.status = status_value
        availability.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        serializer = ProviderAvailabilitySerializer(
            availability
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Provider availability updated successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# LIST PROVIDER AVAILABILITY
# ============================================================

@extend_schema(
    tags=["Provider Availability"],
    summary="List Provider Availability",
    responses={
        200: ProviderAvailabilitySerializer(many=True),
    },
)
class ProviderAvailabilityListAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
    ]

    def get(self, request):

        business = get_object_or_404(
            BusinessProfile,
            owner=request.user,
            is_active=True,
        )

        availabilities = (
            ProviderAvailability.objects.filter(
                business=business,
            )
            .filter(
                Q(employee__isnull=True) |
                Q(employee__is_active=True)
            )
            .select_related(
                "owner",
                "employee",
                "business",
            )
        )

        serializer = ProviderAvailabilitySerializer(
            availabilities,
            many=True,
        )

        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )



# =================================================================================================================
#                           PROVIDER WORKING SCHEDULE
# =================================================================================================================


@extend_schema(
    tags=["Provider Working Schedule"],
    summary="Create Provider Working Schedule",
    request=EmployeeWorkingScheduleSerializer,
    responses={201: EmployeeWorkingScheduleSerializer},
)
class EmployeeWorkingScheduleCreateAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
    ]

    def post(self, request):

        business = get_object_or_404(
            BusinessProfile,
            owner=request.user,
            is_active=True,
        )

        serializer = EmployeeWorkingScheduleSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        employee_uuid = request.data.get(
            "employee_uuid"
        )

        # =====================================================
        # INDIVIDUAL BUSINESS
        # =====================================================

        if business.business_type == BusinessType.INDIVIDUAL:

            if employee_uuid:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Individual business owners cannot "
                            "assign working schedules to employees. "
                            "Please upgrade to a Company or "
                            "Investor business model."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            owner = request.user
            employee = None

        # =====================================================
        # COMPANY / INVESTOR
        # =====================================================

        elif business.business_type in {
            BusinessType.COMPANY,
            BusinessType.INVESTOR,
        }:

            if not employee_uuid:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "employee_uuid is required for "
                            "Company or Investor businesses."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            employee = get_object_or_404(
                Employee,
                employee_uuid=employee_uuid,
                business=business,
                is_active=True,
            )

            owner = None

        else:

            return Response(
                {
                    "success": False,
                    "message": "Invalid business type.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # =====================================================
        # DUPLICATE SLOT CHECK
        # =====================================================

        schedule_filter = {
            "business": business,
            "day_of_week": serializer.validated_data[
                "day_of_week"
            ],
            "slot_type": serializer.validated_data[
                "slot_type"
            ],
            "is_active": True,
        }

        if owner:
            schedule_filter["owner"] = owner
        else:
            schedule_filter["employee"] = employee

        if EmployeeWorkingSchedule.objects.filter(
            **schedule_filter
        ).exists():

            return Response(
                {
                    "success": False,
                    "message": (
                        "This provider already has a "
                        "schedule for this day and slot."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # =====================================================
        # CREATE
        # =====================================================

        schedule = serializer.save(
            business=business,
            owner=owner,
            employee=employee,
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Provider working schedule "
                    "created successfully."
                ),
                "data": EmployeeWorkingScheduleSerializer(
                    schedule
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


# =================================================================================================================
#                           LIST PROVIDER WORKING SCHEDULE
# =================================================================================================================


@extend_schema(
    tags=["Provider Working Schedule"],
    summary="List Provider Working Schedules",
    responses={
        200: EmployeeWorkingScheduleSerializer(
            many=True
        )
    },
)
class EmployeeWorkingScheduleListAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
    ]

    def get(self, request):

        business = get_object_or_404(
            BusinessProfile,
            owner=request.user,
            is_active=True,
        )

        schedules = (
            EmployeeWorkingSchedule.objects
            .filter(
                business=business,
                is_active=True,
            )
            .select_related(
                "business",
                "owner",
                "employee",
            )
            .order_by(
                "day_of_week",
                "start_time",
            )
        )

        serializer = EmployeeWorkingScheduleSerializer(
            schedules,
            many=True,
        )

        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# =================================================================================================================
#                           UPDATE PROVIDER WORKING SCHEDULE
# =================================================================================================================


@extend_schema(
    tags=["Provider Working Schedule"],
    summary="Update Provider Working Schedule",
    request=EmployeeWorkingScheduleSerializer,
    responses={200: EmployeeWorkingScheduleSerializer},
)
class EmployeeWorkingScheduleUpdateAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
    ]

    def post(
        self,
        request,
        employee_working_schedule_uuid,
    ):

        business = get_object_or_404(
            BusinessProfile,
            owner=request.user,
            is_active=True,
        )

        schedule = get_object_or_404(
            EmployeeWorkingSchedule,
            employee_working_schedule_uuid=(
                employee_working_schedule_uuid
            ),
            business=business,
            is_active=True,
        )

        # Provider cannot be changed during update
        if "employee_uuid" in request.data:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Provider cannot be changed while "
                        "updating a schedule."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EmployeeWorkingScheduleSerializer(
            schedule,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True
        )

        schedule = serializer.save()

        return Response(
            {
                "success": True,
                "message": (
                    "Provider working schedule "
                    "updated successfully."
                ),
                "data": EmployeeWorkingScheduleSerializer(
                    schedule
                ).data,
            },
            status=status.HTTP_200_OK,
        )


# =================================================================================================================
#                           DELETE / DEACTIVATE SCHEDULE
# =================================================================================================================


@extend_schema(
    tags=["Provider Working Schedule"],
    summary="Deactivate Provider Working Schedule",
)
class EmployeeWorkingScheduleDeleteAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
    ]

    def delete(
        self,
        request,
        employee_working_schedule_uuid,
    ):

        business = get_object_or_404(
            BusinessProfile,
            owner=request.user,
            is_active=True,
        )

        schedule = get_object_or_404(
            EmployeeWorkingSchedule,
            employee_working_schedule_uuid=(
                employee_working_schedule_uuid
            ),
            business=business,
            is_active=True,
        )

        schedule.is_active = False

        schedule.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Provider working schedule "
                    "deactivated successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )