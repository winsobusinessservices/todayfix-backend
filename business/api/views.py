from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    OpenApiTypes,
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
    BusinessUpgradeIdentity,
    BusinessUpgradeRequest,
    Employee,
    ProviderAvailability,
    EmployeeWorkingSchedule,
)

from ..permissions import IsAdminRole, IsApprovedBusiness, IsEmployeeManagementAllowed
from ..services import (
    BusinessApplicationService,
    BusinessUpgradeService,
    get_current_business_identity,
)
from ..document_utils import serve_document_file

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
    BusinessApplicationDocumentsSerializer,
    BusinessUpgradeRequestSubmitSerializer,
    BusinessUpgradeRequestFullSerializer,
    BusinessUpgradeRequestDocumentsSerializer,
)

from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    CreateAPIView,
    
)

from django.db.models import Q

from django.http import HttpResponse, Http404


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
            "be submitted in ONE multipart/form-data request."
        ),
        request=BusinessApplicationSubmitSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Business application submitted successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "success": True,
                            "message": (
                                "Business application submitted "
                                "successfully."
                            ),
                            "data": {
                                "business_application_uuid": (
                                    "b3f1c2d4-5678-4abc-9def-0123456789ab"
                                ),
                                "business_type": "INDIVIDUAL",
                                "location": "Bengaluru, Karnataka",
                                "status": "PENDING",
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Validation error.",
                examples=[
                    OpenApiExample(
                        "Validation Error",
                        value={
                            "success": False,
                            "message": "Validation error.",
                            "errors": {
                                "business_type": [
                                    "This field is required."
                                ]
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            403: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Permission denied.",
                examples=[
                    OpenApiExample(
                        "Permission Denied",
                        value={
                            "success": False,
                            "message": (
                                "Only USER accounts can submit "
                                "a business application."
                            ),
                        },
                        response_only=True,
                    ),
                ],
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
                            pan_document
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
                            aadhaar_document
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
                            internal_store_photo
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
                            external_store_photo
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
                            cancelled_gst_bill_book_photo
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
                            logo
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
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Business applications fetched successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "success": True,
                            "message": (
                                "Business applications fetched "
                                "successfully."
                            ),
                            "data": [
                                {
                                    "user_uuid": (
                                        "a1b2c3d4-5678-4abc-9def-0123456789ab"
                                    ),
                                    "business_application_uuid": (
                                        "b3f1c2d4-5678-4abc-9def-0123456789ab"
                                    ),
                                    "user_email": "ravi@example.com",
                                    "business_type": "INDIVIDUAL",
                                    "location": "Bengaluru, Karnataka",
                                    "status": "PENDING",
                                    "identity": None,
                                    "bank_account": None,
                                    "created_at": "2026-09-04T10:30:00Z",
                                    "reviewed_at": None,
                                    "rejection_reason": None,
                                }
                            ],
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
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
# LIST MY PENDING APPLICATIONS
# =========================================================

class BusinessApplicationPendingListAPIView(APIView):

    permission_classes = [
        IsAdminRole
    ]

    @extend_schema(
        tags=["Business Administration"],
        summary="List pending business applications",
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Pending applications fetched successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "success": True,
                            "message": (
                                "Pending business applications "
                                "fetched successfully."
                            ),
                            "data": [
                                {
                                    "user_uuid": (
                                        "a1b2c3d4-5678-4abc-9def-0123456789ab"
                                    ),
                                    "business_application_uuid": (
                                        "b3f1c2d4-5678-4abc-9def-0123456789ab"
                                    ),
                                    "user_email": "ravi@example.com",
                                    "business_type": "COMPANY",
                                    "location": "Bengaluru, Karnataka",
                                    "status": "PENDING",
                                    "identity": None,
                                    "bank_account": None,
                                    "created_at": "2026-09-04T10:30:00Z",
                                    "reviewed_at": None,
                                    "rejection_reason": None,
                                }
                            ],
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def get(self, request):

        applications = (
            BusinessApplication.objects
            .filter(
                status=BusinessApplicationStatus.PENDING,
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
# ADMIN
# LIST ACCEPTED BUSINESS APPLICATIONS
# =========================================================

class BusinessApplicationAcceptedListAPIView(APIView):

    permission_classes = [
        IsAdminRole
    ]

    @extend_schema(
        tags=["Business Administration"],
        summary="List accepted business applications",
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Accepted applications fetched successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "success": True,
                            "message": (
                                "Accepted business applications "
                                "fetched successfully."
                            ),
                            "data": [
                                {
                                    "user_uuid": (
                                        "a1b2c3d4-5678-4abc-9def-0123456789ab"
                                    ),
                                    "business_application_uuid": (
                                        "b3f1c2d4-5678-4abc-9def-0123456789ab"
                                    ),
                                    "user_email": "ravi@example.com",
                                    "business_type": "COMPANY",
                                    "location": "Bengaluru, Karnataka",
                                    "status": "APPROVED",
                                    "identity": None,
                                    "bank_account": None,
                                    "created_at": "2026-09-04T10:30:00Z",
                                    "reviewed_at": "2026-09-04T12:00:00Z",
                                    "rejection_reason": None,
                                }
                            ],
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )

    def get(self, request):

        applications = (
            BusinessApplication.objects
            .filter(
                status=BusinessApplicationStatus.APPROVED,
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
# ADMIN
# LIST REJECTED BUSINESS APPLICATIONS
# =========================================================

class BusinessApplicationRejectedListAPIView(APIView):

    permission_classes = [
        IsAdminRole
    ]

    @extend_schema(
        tags=["Business Administration"],
        summary="List rejected business applications",
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Rejected applications fetched successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "success": True,
                            "message": (
                                "Rejected business applications "
                                "fetched successfully."
                            ),
                            "data": [
                                {
                                    "user_uuid": (
                                        "a1b2c3d4-5678-4abc-9def-0123456789ab"
                                    ),
                                    "business_application_uuid": (
                                        "b3f1c2d4-5678-4abc-9def-0123456789ab"
                                    ),
                                    "user_email": "ravi@example.com",
                                    "business_type": "COMPANY",
                                    "location": "Bengaluru, Karnataka",
                                    "status": "REJECTED",
                                    "identity": None,
                                    "bank_account": None,
                                    "created_at": "2026-09-04T10:30:00Z",
                                    "reviewed_at": "2026-09-04T12:00:00Z",
                                    "rejection_reason": "Invalid documents.",
                                }
                            ],
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def get(self, request):

        applications = (
            BusinessApplication.objects
            .filter(
                status=BusinessApplicationStatus.REJECTED,
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
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Business application fetched successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "success": True,
                            "message": (
                                "Business application fetched "
                                "successfully."
                            ),
                            "data": {
                                "user_uuid": (
                                    "a1b2c3d4-5678-4abc-9def-0123456789ab"
                                ),
                                "business_application_uuid": (
                                    "b3f1c2d4-5678-4abc-9def-0123456789ab"
                                ),
                                "user_email": "ravi@example.com",
                                "business_type": "INDIVIDUAL",
                                "location": "Bengaluru, Karnataka",
                                "status": "PENDING",
                                "identity": None,
                                "bank_account": None,
                                "created_at": "2026-09-04T10:30:00Z",
                                "reviewed_at": None,
                                "rejection_reason": None,
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
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
            .select_related(
                "category",
                "owner",
            )
        )

        serializer = (
            BusinessProfileSerializer(
                profiles,
                many=True,
                context={
                    "request": request,
                },
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
    responses={
        201: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Employee created successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Employee created successfully.",
                        "data": {
                            "employee_uuid": (
                                "f5a6b7c8-5678-4abc-9def-0123456789ab"
                            ),
                            "name": "Mahesh",
                            "phone": "9988776655",
                            "email": "mahesh@example.com",
                            "is_active": True,
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
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

        try:
            employee = serializer.save(
                business=business,
            )
        except IntegrityError:
            return Response(
                {
                    "success": False,
                    "message": (
                        "An employee with this phone number "
                        "already exists in your business."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
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
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Employees fetched successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "data": [
                            {
                                "employee_uuid": (
                                    "f5a6b7c8-5678-4abc-9def-0123456789ab"
                                ),
                                "name": "Mahesh",
                                "phone": "9988776655",
                                "email": "mahesh@example.com",
                                "is_active": True,
                            }
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
    },
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
        ).order_by("-created_at")

#=================================================================
#               Update Employees API View
#=================================================================
@extend_schema(
    tags=["Business Employees"],
    summary="Update Employee",
    description="Update an employee belonging to the authenticated business.",
    request=EmployeeUpdateSerializer,
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Employee updated successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Employee updated successfully.",
                        "data": {
                            "employee_uuid": (
                                "f5a6b7c8-5678-4abc-9def-0123456789ab"
                            ),
                            "name": "Mahesh Kumar",
                            "phone": "9988776655",
                            "email": "mahesh@example.com",
                            "is_active": True,
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
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
    summary="Delete Employee",
    description="Deactivate an employee belonging to the authenticated business.",
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Employee deleted successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Employee deleted successfully.",
                    },
                    response_only=True,
                ),
            ],
        ),
    },
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
    tags=["Service Provider Availability"],
    summary="Create Provider Availability",
    request=ProviderAvailabilitySerializer,
    responses={
        201: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Provider availability created successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": (
                            "Provider availability created successfully."
                        ),
                        "data": {
                            "provider_availability_uuid": (
                                "a1b2c3d4-5678-4abc-9def-0123456789ab"
                            ),
                            "employee_uuid": (
                                "f5a6b7c8-5678-4abc-9def-0123456789ab"
                            ),
                            "status": "AVAILABLE",
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
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
    tags=["Service Provider Availability"],
    summary="Update Provider Availability",
    request=ProviderAvailabilitySerializer,
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Provider availability updated successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": (
                            "Provider availability updated successfully."
                        ),
                        "data": {
                            "provider_availability_uuid": (
                                "a1b2c3d4-5678-4abc-9def-0123456789ab"
                            ),
                            "employee_uuid": (
                                "f5a6b7c8-5678-4abc-9def-0123456789ab"
                            ),
                            "status": "BUSY",
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
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
    tags=["Service Provider Availability"],
    summary="List Provider Availability",
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Provider availability fetched successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "data": [
                            {
                                "provider_availability_uuid": (
                                    "a1b2c3d4-5678-4abc-9def-0123456789ab"
                                ),
                                "employee_uuid": (
                                    "f5a6b7c8-5678-4abc-9def-0123456789ab"
                                ),
                                "status": "AVAILABLE",
                            }
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
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
    responses={
        201: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Provider working schedule created successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": (
                            "Provider working schedule "
                            "created successfully."
                        ),
                        "data": {
                            "employee_working_schedule_uuid": (
                                "a1b2c3d4-5678-4abc-9def-0123456789ab"
                            ),
                            "business_uuid": (
                                "b2c3d4e5-6789-4abc-9def-0123456789ab"
                            ),
                            "owner_uuid": (
                                "c3d4e5f6-7890-4abc-9def-0123456789ab"
                            ),
                            "employee": None,
                            "day_of_week": "MONDAY",
                            "slot_type": "FULL_DAY",
                            "start_time": "09:00:00",
                            "end_time": "18:00:00",
                            "is_active": True,
                            "created_at": "2026-09-04T09:00:00Z",
                            "updated_at": "2026-09-04T09:00:00Z",
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
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
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Provider working schedules fetched successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "data": [
                            {
                                "employee_working_schedule_uuid": (
                                    "a1b2c3d4-5678-4abc-9def-0123456789ab"
                                ),
                                "business_uuid": (
                                    "b2c3d4e5-6789-4abc-9def-0123456789ab"
                                ),
                                "owner_uuid": (
                                    "c3d4e5f6-7890-4abc-9def-0123456789ab"
                                ),
                                "employee": None,
                                "day_of_week": "MONDAY",
                                "slot_type": "FULL_DAY",
                                "start_time": "09:00:00",
                                "end_time": "18:00:00",
                                "is_active": True,
                                "created_at": "2026-09-04T09:00:00Z",
                                "updated_at": "2026-09-04T09:00:00Z",
                            }
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
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
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Provider working schedule updated successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": (
                            "Provider working schedule "
                            "updated successfully."
                        ),
                        "data": {
                            "employee_working_schedule_uuid": (
                                "a1b2c3d4-5678-4abc-9def-0123456789ab"
                            ),
                            "business_uuid": (
                                "b2c3d4e5-6789-4abc-9def-0123456789ab"
                            ),
                            "owner_uuid": (
                                "c3d4e5f6-7890-4abc-9def-0123456789ab"
                            ),
                            "employee": None,
                            "day_of_week": "MONDAY",
                            "slot_type": "FULL_DAY",
                            "start_time": "10:00:00",
                            "end_time": "19:00:00",
                            "is_active": True,
                            "created_at": "2026-09-04T09:00:00Z",
                            "updated_at": "2026-09-04T10:00:00Z",
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
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
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Provider working schedule deactivated successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": (
                            "Provider working schedule "
                            "deactivated successfully."
                        ),
                    },
                    response_only=True,
                ),
            ],
        ),
    },
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
        )

        schedule.delete()

        return Response(
            {
                "success": True,
                "message": (
                    "Provider working schedule "
                    "deleted successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )

# =========================================================
# VIEW BUSINESS APPLICATION DOCUMENTS
# ADMIN + BUSINESS OWNER
# =========================================================
@extend_schema(
    tags=["Business Application"],
    summary="View business application documents",
    description=(
        "Admins can view documents of any business application. "
        "A business owner can view documents of their own application."
    ),
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Business application documents fetched successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": (
                            "Business application documents "
                            "fetched successfully."
                        ),
                        "data": {
                            "pan_document": {
                                "url": "https://example.com/pan.pdf",
                                "name": "pan.pdf",
                                "type": "application/pdf",
                            },
                            "aadhaar_document": {
                                "url": "https://example.com/aadhaar.pdf",
                                "name": "aadhaar.pdf",
                                "type": "application/pdf",
                            },
                            "internal_store_photo": {
                                "url": "https://example.com/internal.jpg",
                                "name": "internal.jpg",
                                "type": "image/jpeg",
                            },
                            "external_store_photo": {
                                "url": "https://example.com/external.jpg",
                                "name": "external.jpg",
                                "type": "image/jpeg",
                            },
                            "cancelled_gst_bill_book_photo": {
                                "url": "https://example.com/gst-bill.jpg",
                                "name": "gst-bill.jpg",
                                "type": "image/jpeg",
                            },
                            "logo": {
                                "url": "https://example.com/logo.png",
                                "name": "logo.png",
                                "type": "image/png",
                            },
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class BusinessApplicationDocumentsAPIView(APIView):
    permission_classes = [
        IsAuthenticated
    ]

    @extend_schema(
        tags=["Business Application"],
        summary="View business application documents",
        description=(
            "Admins can view documents of any business application. "
            "A business owner can view documents of their own application."
        ),
        responses=BusinessApplicationDocumentsSerializer,
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
                "identity",
            ),
            business_application_uuid=business_application_uuid,
        )

        # -------------------------------------------------
        # ACCESS CHECK
        # -------------------------------------------------

        is_admin = (
            request.user.role == UserRole.ADMIN
        )

        is_owner = (
            application.user_id == request.user.id
        )

        if not is_admin and not is_owner:
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "view these documents."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # -------------------------------------------------
        # DOCUMENTS
        # -------------------------------------------------

        try:
            identity = application.identity

        except BusinessIdentity.DoesNotExist:
            return Response(
                {
                    "success": True,
                    "message": (
                        "No documents have been uploaded "
                        "for this business application."
                    ),
                    "data": None,
                },
                status=status.HTTP_200_OK,
            )

        serializer = BusinessApplicationDocumentsSerializer(
            identity,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Business application documents "
                    "fetched successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# =========================================================
# BUSINESS APPLICATION - VIEW A SINGLE DOCUMENT (STREAMED)
# =========================================================

BUSINESS_APPLICATION_DOCUMENT_FIELDS = {
    "pan": "pan_document",
    "aadhaar": "aadhaar_document",
    "internal_store_photo": "internal_store_photo",
    "external_store_photo": "external_store_photo",
    "gst_bill_book": "cancelled_gst_bill_book_photo",
    "logo": "logo",
}


class BusinessApplicationDocumentViewAPIView(APIView):
    """
    Streams the actual file for ONE document belonging to a
    business application, instead of returning a public URL.

    Every request re-checks that the caller is either the
    application's own owner or an Admin - there is no way to
    view this file without a valid, permitted access token.
    """

    permission_classes = [
        IsAuthenticated
    ]

    @extend_schema(
        tags=["Business Application"],
        summary="View a single business application document",
        description=(
            "Streams the requested document inline (PDF/image "
            "preview) rather than returning a public link. "
            "Admins can view any application's documents. "
            "A business owner can only view their own."
        ),
    )
    def get(
        self,
        request,
        business_application_uuid,
        document_key,
    ):
        field_name = BUSINESS_APPLICATION_DOCUMENT_FIELDS.get(
            document_key
        )

        if field_name is None:
            return Response(
                {
                    "success": False,
                    "message": (
                        f"Unknown document type '{document_key}'. "
                        f"Valid options: "
                        f"{', '.join(BUSINESS_APPLICATION_DOCUMENT_FIELDS)}"
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        application = get_object_or_404(
            BusinessApplication.objects.select_related(
                "user",
                "identity",
            ),
            business_application_uuid=business_application_uuid,
        )

        # -------------------------------------------------
        # ACCESS CHECK - same rule as the metadata endpoint
        # -------------------------------------------------

        is_admin = request.user.role == UserRole.ADMIN
        is_owner = application.user_id == request.user.id

        if not is_admin and not is_owner:
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "view this document."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            identity = application.identity
        except BusinessIdentity.DoesNotExist:
            raise Http404(
                "No documents have been uploaded for "
                "this business application."
            )

        file_field = getattr(identity, field_name)

        return serve_document_file(file_field)


# =========================================================
# BUSINESS OWNER
# SUBMIT BUSINESS TYPE UPGRADE REQUEST
# =========================================================

@extend_schema(
    tags=["Business Upgrade Request"],
    summary="Create Business Upgrade Request",
    request=BusinessUpgradeRequestSubmitSerializer,
    responses={
        201: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Business upgrade request created successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": (
                            "Business upgrade request "
                            "created successfully."
                        ),
                        "data": {
                            "business_upgrade_request_uuid": (
                                "a1b2c3d4-5678-4abc-9def-0123456789ab"
                            ),
                            "business_uuid": (
                                "b2c3d4e5-6789-4abc-9def-0123456789ab"
                            ),
                            "owner_uuid": (
                                "c3d4e5f6-7890-4abc-9def-0123456789ab"
                            ),
                            "current_business_type": "INDIVIDUAL",
                            "requested_business_type": "COMPANY",
                            "keep_employees_and_schedules": True,
                            "bank_details_changed": False,
                            "status": "PENDING",
                            "created_at": "2026-09-04T10:00:00Z",
                            "reviewed_at": None,
                            "rejection_reason": None,
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class BusinessUpgradeRequestCreateAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]

    @extend_schema(
        tags=["Business Upgrade Request"],
        summary="Request a business type change",
        description=(
            "Submitted by an approved business owner to request "
            "changing their business_type (e.g. INDIVIDUAL to "
            "COMPANY). Only fields missing from the business's "
            "existing identity need to be submitted."
        ),
        request=BusinessUpgradeRequestSubmitSerializer,
        responses={
            201: BusinessUpgradeRequestFullSerializer,
            400: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Validation error"
            ),
        },
    )
    def post(self, request):

        business = get_object_or_404(
            BusinessProfile,
            owner=request.user,
            is_active=True,
        )

        current_identity = get_current_business_identity(
            business
        )

        serializer = BusinessUpgradeRequestSubmitSerializer(
            data=request.data,
            context={
                "business": business,
                "current_identity": current_identity,
            },
        )

        serializer.is_valid(raise_exception=True)

        try:

            upgrade_request = BusinessUpgradeService.submit(
                business=business,
                validated_data=serializer.validated_data,
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
                    "Business upgrade request submitted "
                    "successfully. It is waiting for admin "
                    "review."
                ),
                "data": (
                    BusinessUpgradeRequestFullSerializer(
                        upgrade_request
                    ).data
                ),
            },
            status=status.HTTP_201_CREATED,
        )


# =========================================================
# BUSINESS OWNER
# LIST MY UPGRADE REQUESTS
# =========================================================

@extend_schema(
    tags=["Business Upgrade Request"],
    summary="List Business Upgrade Requests",
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Business upgrade requests fetched successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "data": [
                            {
                                "business_upgrade_request_uuid": (
                                    "a1b2c3d4-5678-4abc-9def-0123456789ab"
                                ),
                                "business_uuid": (
                                    "b2c3d4e5-6789-4abc-9def-0123456789ab"
                                ),
                                "owner_uuid": (
                                    "c3d4e5f6-7890-4abc-9def-0123456789ab"
                                ),
                                "current_business_type": "INDIVIDUAL",
                                "requested_business_type": "COMPANY",
                                "keep_employees_and_schedules": True,
                                "bank_details_changed": False,
                                "status": "PENDING",
                                "created_at": "2026-09-04T10:00:00Z",
                                "reviewed_at": None,
                                "rejection_reason": None,
                            }
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class BusinessUpgradeRequestListAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsApprovedBusiness,
    ]

    @extend_schema(
        tags=["Business Upgrade Request"],
        summary="List my business upgrade requests",
        responses=BusinessUpgradeRequestFullSerializer(
            many=True
        ),
    )
    def get(self, request):

        upgrade_requests = (
            BusinessUpgradeRequest.objects
            .filter(
                business__owner=request.user,
            )
            .select_related(
                "business",
                "business__owner",
                "reviewed_by",
            )
        )

        serializer = BusinessUpgradeRequestFullSerializer(
            upgrade_requests,
            many=True,
        )

        return Response(
            {
                "success": True,
                "data": serializer.data,
            }
        )


# =========================================================
# BUSINESS UPGRADE REQUEST - DOCUMENTS
# =========================================================

BUSINESS_UPGRADE_DOCUMENT_FIELDS = {
    "pan": "pan_document",
    "aadhaar": "aadhaar_document",
    "internal_store_photo": "internal_store_photo",
    "external_store_photo": "external_store_photo",
    "gst_bill_book": "cancelled_gst_bill_book_photo",
}


def _get_upgrade_request_for_user(request, business_upgrade_request_uuid):
    """
    Shared lookup + permission check for both upgrade-request
    document endpoints below. Returns the BusinessUpgradeRequest,
    or raises Http404 / returns a 403 Response.
    """
    upgrade_request = get_object_or_404(
        BusinessUpgradeRequest.objects.select_related(
            "business",
            "business__owner",
        ),
        business_upgrade_request_uuid=business_upgrade_request_uuid,
    )

    is_admin = request.user.role == UserRole.ADMIN
    is_owner = upgrade_request.business.owner_id == request.user.id

    if not is_admin and not is_owner:
        return upgrade_request, Response(
            {
                "success": False,
                "message": (
                    "You do not have permission to "
                    "view these documents."
                ),
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    return upgrade_request, None


@extend_schema(
    tags=["Business Upgrade Request"],
    summary="View Business Upgrade Request Documents",
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Business upgrade request documents fetched successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": (
                            "Business upgrade request documents "
                            "fetched successfully."
                        ),
                        "data": {
                            "pan_document": {
                                "url": "https://example.com/pan.pdf",
                                "name": "pan.pdf",
                                "type": "application/pdf",
                            },
                            "aadhaar_document": {
                                "url": "https://example.com/aadhaar.pdf",
                                "name": "aadhaar.pdf",
                                "type": "application/pdf",
                            },
                            "internal_store_photo": {
                                "url": "https://example.com/internal.jpg",
                                "name": "internal.jpg",
                                "type": "image/jpeg",
                            },
                            "external_store_photo": {
                                "url": "https://example.com/external.jpg",
                                "name": "external.jpg",
                                "type": "image/jpeg",
                            },
                            "cancelled_gst_bill_book_photo": {
                                "url": "https://example.com/gst-bill.jpg",
                                "name": "gst-bill.jpg",
                                "type": "image/jpeg",
                            },
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class BusinessUpgradeRequestDocumentsAPIView(APIView):
    """
    Lists the documents submitted with an upgrade request, each
    with a link to the protected streaming view below - not a
    public /media/ URL.
    """

    permission_classes = [
        IsAuthenticated
    ]

    @extend_schema(
        tags=["Business Upgrade Request"],
        summary="List documents for a business upgrade request",
        responses=BusinessUpgradeRequestDocumentsSerializer,
    )
    def get(self, request, business_upgrade_request_uuid):

        upgrade_request, error_response = (
            _get_upgrade_request_for_user(
                request, business_upgrade_request_uuid
            )
        )
        if error_response:
            return error_response

        try:
            identity = upgrade_request.identity
        except BusinessUpgradeIdentity.DoesNotExist:
            return Response(
                {
                    "success": True,
                    "message": (
                        "No new documents were submitted with "
                        "this upgrade request."
                    ),
                    "data": {},
                },
                status=status.HTTP_200_OK,
            )

        serializer = BusinessUpgradeRequestDocumentsSerializer(
            identity,
            context={"request": request},
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Business upgrade request documents "
                    "fetched successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class BusinessUpgradeRequestDocumentViewAPIView(APIView):
    """
    Streams the actual file for ONE document belonging to a
    business upgrade request. Same protection model as the
    business application documents view: owner or Admin only,
    re-checked on every request.
    """

    permission_classes = [
        IsAuthenticated
    ]

    @extend_schema(
        tags=["Business Upgrade Request"],
        summary="View a single business upgrade request document",
        description=(
            "Streams the requested document inline (PDF/image "
            "preview). The business owner who submitted the "
            "upgrade request, or an Admin, can view it."
        ),
    )
    def get(
        self,
        request,
        business_upgrade_request_uuid,
        document_key,
    ):
        field_name = BUSINESS_UPGRADE_DOCUMENT_FIELDS.get(
            document_key
        )

        if field_name is None:
            return Response(
                {
                    "success": False,
                    "message": (
                        f"Unknown document type '{document_key}'. "
                        f"Valid options: "
                        f"{', '.join(BUSINESS_UPGRADE_DOCUMENT_FIELDS)}"
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        upgrade_request, error_response = (
            _get_upgrade_request_for_user(
                request, business_upgrade_request_uuid
            )
        )
        if error_response:
            return error_response

        try:
            identity = upgrade_request.identity
        except BusinessUpgradeIdentity.DoesNotExist:
            raise Http404(
                "No documents have been uploaded for "
                "this upgrade request."
            )

        file_field = getattr(identity, field_name)

        return serve_document_file(file_field)


# =========================================================
# ADMIN
# LIST UPGRADE REQUESTS
# =========================================================
@extend_schema(
    tags=["Business Administration"],
    summary="List business upgrade requests",
    description=(
        "Optional query param `status` filters by "
        "PENDING, APPROVED, or REJECTED."
    ),
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Business upgrade requests fetched successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "data": [
                            {
                                "business_upgrade_request_uuid": (
                                    "a1b2c3d4-5678-4abc-9def-0123456789ab"
                                ),
                                "business_uuid": (
                                    "b2c3d4e5-6789-4abc-9def-0123456789ab"
                                ),
                                "business_name": "ABC Services",
                                "owner_uuid": (
                                    "c3d4e5f6-7890-4abc-9def-0123456789ab"
                                ),
                                "current_business_type": "INDIVIDUAL",
                                "requested_business_type": "COMPANY",
                                "keep_employees_and_schedules": True,
                                "bank_details_changed": False,
                                "status": "PENDING",
                                "created_at": "2026-09-04T10:00:00Z",
                                "reviewed_at": None,
                                "rejection_reason": None,
                            }
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class AdminBusinessUpgradeRequestListAPIView(APIView):

    permission_classes = [
        IsAdminRole
    ]

    @extend_schema(
        tags=["Business Administration"],
        summary="List business upgrade requests",
        description=(
            "Optional query param `status` filters by "
            "PENDING, APPROVED, or REJECTED."
        ),
        responses=BusinessUpgradeRequestFullSerializer(
            many=True
        ),
    )
    def get(self, request):

        upgrade_requests = (
            BusinessUpgradeRequest.objects
            .select_related(
                "business",
                "business__owner",
                "reviewed_by",
            )
        )

        status_filter = request.query_params.get("status")

        if status_filter:
            upgrade_requests = upgrade_requests.filter(
                status=status_filter.upper()
            )

        serializer = BusinessUpgradeRequestFullSerializer(
            upgrade_requests,
            many=True,
        )

        return Response(
            {
                "success": True,
                "data": serializer.data,
            }
        )


# =========================================================
# ADMIN
# APPROVE UPGRADE REQUEST
# =========================================================
@extend_schema(
    tags=["Business Administration"],
    summary="Approve business upgrade request",
    description=(
        "Approving changes the business's business_type "
        "and, depending on the request, may update bank "
        "details (resetting verification) and deactivate "
        "existing employees/schedules."
    ),
    request=None,
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Business upgrade request approved successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": (
                            "Business upgrade request approved. "
                            "Business type is now COMPANY."
                        ),
                        "data": {
                            "business_upgrade_request_uuid": (
                                "a1b2c3d4-5678-4abc-9def-0123456789ab"
                            ),
                            "business_uuid": (
                                "b2c3d4e5-6789-4abc-9def-0123456789ab"
                            ),
                            "business_name": "ABC Services",
                            "owner_uuid": (
                                "c3d4e5f6-7890-4abc-9def-0123456789ab"
                            ),
                            "current_business_type": "INDIVIDUAL",
                            "requested_business_type": "COMPANY",
                            "keep_employees_and_schedules": True,
                            "bank_details_changed": False,
                            "status": "APPROVED",
                            "created_at": "2026-09-04T10:00:00Z",
                            "reviewed_at": "2026-09-04T11:00:00Z",
                            "rejection_reason": None,
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class AdminApproveBusinessUpgradeRequestAPIView(APIView):

    permission_classes = [
        IsAdminRole
    ]

    @extend_schema(
        tags=["Business Administration"],
        summary="Approve business upgrade request",
        description=(
            "Approving changes the business's business_type "
            "and, depending on the request, may update bank "
            "details (resetting verification) and deactivate "
            "existing employees/schedules."
        ),
        request=None,
        responses=BusinessUpgradeRequestFullSerializer,
    )
    def post(self, request, business_upgrade_request_uuid):

        upgrade_request = get_object_or_404(
            BusinessUpgradeRequest,
            business_upgrade_request_uuid=(
                business_upgrade_request_uuid
            ),
        )

        try:

            upgrade_request, business = (
                BusinessUpgradeService.approve(
                    upgrade_request=upgrade_request,
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
                    "Business upgrade request approved. "
                    "Business type is now "
                    f"{business.business_type}."
                ),
                "data": (
                    BusinessUpgradeRequestFullSerializer(
                        upgrade_request
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )


# =========================================================
# ADMIN
# REJECT UPGRADE REQUEST
# =========================================================
@extend_schema(
    tags=["Business Administration"],
    summary="Reject business upgrade request",
    description="Admin must provide a rejection reason.",
    request=RejectBusinessApplicationSerializer,
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Business upgrade request rejected successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": (
                            "Business upgrade request rejected."
                        ),
                        "data": {
                            "business_upgrade_request_uuid": (
                                "a1b2c3d4-5678-4abc-9def-0123456789ab"
                            ),
                            "business_uuid": (
                                "b2c3d4e5-6789-4abc-9def-0123456789ab"
                            ),
                            "business_name": "ABC Services",
                            "owner_uuid": (
                                "c3d4e5f6-7890-4abc-9def-0123456789ab"
                            ),
                            "current_business_type": "INDIVIDUAL",
                            "requested_business_type": "COMPANY",
                            "keep_employees_and_schedules": True,
                            "bank_details_changed": False,
                            "status": "REJECTED",
                            "created_at": "2026-09-04T10:00:00Z",
                            "reviewed_at": "2026-09-04T11:00:00Z",
                            "rejection_reason": "Invalid business documents.",
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class AdminRejectBusinessUpgradeRequestAPIView(APIView):

    permission_classes = [
        IsAdminRole
    ]

    @extend_schema(
        tags=["Business Administration"],
        summary="Reject business upgrade request",
        description=(
            "Admin must provide a rejection reason."
        ),
        request=RejectBusinessApplicationSerializer,
        responses=BusinessUpgradeRequestFullSerializer,
    )
    def post(self, request, business_upgrade_request_uuid):

        upgrade_request = get_object_or_404(
            BusinessUpgradeRequest,
            business_upgrade_request_uuid=(
                business_upgrade_request_uuid
            ),
        )

        serializer = RejectBusinessApplicationSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        try:

            upgrade_request = (
                BusinessUpgradeService.reject(
                    upgrade_request=upgrade_request,
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
                    "Business upgrade request rejected."
                ),
                "data": (
                    BusinessUpgradeRequestFullSerializer(
                        upgrade_request
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )