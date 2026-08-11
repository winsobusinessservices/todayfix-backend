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
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.choices import UserRole

from ..choices import BusinessApplicationStatus
from ..models import (
    BusinessApplication,
    BusinessBankAccount,
    BusinessIdentity,
    BusinessProfile,
)
from ..permissions import IsAdminRole
from ..services import BusinessApplicationService

from .serializers import (
    BusinessApplicationFullSerializer,
    BusinessApplicationSubmitSerializer,
    BusinessProfileSerializer,
    RejectBusinessApplicationSerializer,
)


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

                application = (
                    BusinessApplicationService.submit(
                        user=request.user,
                        business_type=data[
                            "business_type"
                        ],
                    )
                )

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

                        pan_document=data.get(
                            "pan_document"
                        ),

                        aadhaar_number=data.get(
                            "aadhaar_number",
                            "",
                        ),

                        aadhaar_document=data.get(
                            "aadhaar_document"
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

                        internal_store_photo=data.get(
                            "internal_store_photo"
                        ),

                        external_store_photo=data.get(
                            "external_store_photo"
                        ),

                        cancelled_gst_bill_book_photo=(
                            data.get(
                                "cancelled_gst_bill_book_photo"
                            )
                        ),

                        logo=data.get(
                            "logo"
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
        uuid,
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
            uuid=uuid,
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
        uuid,
    ):

        application = get_object_or_404(
            BusinessApplication,
            uuid=uuid,
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
                    profile.uuid
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
        uuid,
    ):

        application = get_object_or_404(
            BusinessApplication,
            uuid=uuid,
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
        uuid,
    ):

        profile = get_object_or_404(
            BusinessProfile,
            uuid=uuid,
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

        