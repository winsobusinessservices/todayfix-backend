from accounts.models import GoogleIdentity
from django.contrib.auth import get_user_model
from rest_framework.compat import requests
from accounts.api.serializers import GoogleLoginSerializer
import logging
from accounts.choices import UserRole
from accounts.document_utils import get_profile_picture_url
from common.document_utils import serve_document_file
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
    OpenApiTypes,
)
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
)
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import IntegrityError, transaction

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from accounts.models import (
    CustomUser,
    PasswordResetToken,
    EmailTemplate,
    Address,
)
from accounts.services import (
    AuthService,
    OTPService,
    SignupOTPService,
)
from .serializers import (
    RegisterUserSerializer,
    LoginSerializer,
    LogoutSerializer,
    UpdateProfileSerializer,
    UnifiedPasswordResetSerializer,
    ForgotPasswordSerializer,
    AddressSerializer,
    VerifyEmailSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
    LoginSendOTPSerializer,
    SignupVerifyOTPSerializer,
    GoogleLoginSerializer,
    GoogleLoginSerializer,
    SignupVerifyOTPSerializer,
    VerifyPhoneUpdateOTPSerializer,
)
from google.oauth2 import id_token
from google.auth.transport import requests
logger = logging.getLogger(__name__)
# =========================================================
# REGISTER USER
# =========================================================
@extend_schema(
    auth=[],
    tags=["SignUp"],
    summary="Register User",
    description=(
        "Creates a pending user registration and sends an "
        "email verification link."
    ),
    request=RegisterUserSerializer,
    responses={
        201: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Verification email sent successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": (
                            "Verification email sent successfully. "
                            "Please check your email to complete registration."
                        ),
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class RegisterUserAPIView(CreateAPIView):
    serializer_class = RegisterUserSerializer
    def create(
        self,
        request,
        *args,
        **kwargs
    ):
        serializer = self.get_serializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )
        result = serializer.save()
        # -----------------------------------------------------
        # EMAIL REGISTRATION
        # -----------------------------------------------------
        pending_registration = result
        # -----------------------------------------------------
        # PHONE REGISTRATION
        # -----------------------------------------------------
        if pending_registration.verification_method == "phone":
            phone = pending_registration.phone
            if not SignupOTPService.can_send_otp(phone):
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Please wait 60 seconds "
                            "before requesting another OTP."
                        ),
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            otp = SignupOTPService.create_otp(
                phone=phone
            )
            print(
                f"\n{'=' * 50}\n"
                f"SIGNUP OTP\n"
                f"Phone: {phone}\n"
                f"OTP: {otp}\n"
                f"Expires: 5 minutes\n"
                f"{'=' * 50}\n"
            )
            logger.debug(
                "SIGNUP OTP | Phone: %s | OTP: %s | Expires: 5 min",
                phone, otp,
            )
            return Response(
                {
                    "success": True,
                    "message": "OTP sent successfully.",
                },
                status=status.HTTP_201_CREATED,
            )
        verification_link = (
            f"{settings.FRONTEND_DOMAIN}/verify-email/"
            f"?pending_registration_uuid={pending_registration.pending_registration_uuid}"
            f"&token={pending_registration.token}"
        )
        template = EmailTemplate.objects.get(
            name="REGISTRATION_VERIFICATION"
        )
        message = template.message.replace(
            "{{ first_name }}",
            pending_registration.first_name or "User",
        ).replace(
            "{{ verification_link }}",
            verification_link,
        ).replace(
            "{{ expiry_hours }}",
            "15 minutes",
        )
        html_message = render_to_string(
            "emails/base_email.html",
            {
                "subject": template.subject,
                "logo_url": settings.EMAIL_LOGO_URL,
                "first_name": (
                    pending_registration.first_name
                    or "User"
                ),
                "message": message,
                "otp": "",
                "verification_link": verification_link,
                "additional_message": "",
            },
        )
        email_message = EmailMultiAlternatives(
            subject=template.subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[pending_registration.email],
        )
        email_message.attach_alternative(
            html_message,
            "text/html",
        )
        email_message.send(
            fail_silently=False
        )
        return Response(
            {
                "success": True,
                "message": (
                    "Verification email sent successfully. "
                    "Please check your email to complete registration."
                ),
            },
            status=status.HTTP_201_CREATED,
        )
# =========================================================
# VERIFY EMAIL
# =========================================================
@extend_schema(
    auth=[],
    tags=["SignUp"],
    summary="Verify Email",
    description=(
        "Verifies the user's email using the UUID and "
        "verification token received by email."
    ),
    request=VerifyEmailSerializer,

    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Email verified successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Signup successful.",
                        "data": {
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "user": {
                                "id": 12,
                                "user_uuid": "b3f1c2d4-5678-4abc-9def-0123456789ab",
                                "first_name": "Ravi",
                                "last_name": "Kumar",
                                "email": "ravi.kumar@example.com",
                                "phone": "9876543210",
                                "role": "CUSTOMER",
                                "profileImage": "",
                            },
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)


class VerifyEmailAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = VerifyEmailSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )
        pending_registration_uuid = serializer.validated_data[
            "pending_registration_uuid"
        ]
        token = serializer.validated_data[
            "token"
        ]
        user = AuthService.verify_email_registration(
            pending_registration_uuid=pending_registration_uuid,
            token=token,
        )
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        return Response(
            {
                "success": True,
                "message": "Signup successful.",
                "data": {
                    "access": str(access),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "user_uuid": str(user.user_uuid),
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "phone": user.phone,
                        "role": user.role,
                        "profileImage": get_profile_picture_url(user, request)
                    },
                },
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# LOGIN
# =========================================================
@extend_schema(
    auth=[],
    tags=["Login"],
    summary="Login",
    description="Login using email and password.",
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Login successful.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Login successful.",
                        "data": {
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "user": {
                                "id": 12,
                                "user_uuid": "b3f1c2d4-5678-4abc-9def-0123456789ab",
                                "first_name": "Ravi",
                                "last_name": "Kumar",
                                "email": "ravi.kumar@example.com",
                                "phone": "9876543210",
                                "role": "CUSTOMER",
                                "profileImage": "",
                            },
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class LoginAPIView(CreateAPIView):
    serializer_class = LoginSerializer
    def create(
        self,
        request,
        *args,
        **kwargs
    ):
        serializer = self.get_serializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )
        user = serializer.validated_data[
            "user"
        ]
        refresh = RefreshToken.for_user(
            user
        )
        access = refresh.access_token
        return Response(
            {
                "success": True,
                "message": "Login successful.",
                "data": {
                    "access": str(access),
                    "refresh": str(refresh),
                    "user":{
                        "id": user.id,
                        "user_uuid": str(user.user_uuid),
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "phone": user.phone,
                        "role": user.role,
                        "profileImage": (
                            user.profile_picture.url
                            if user.profile_picture
                            else ""
                        )
                    }
                },
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# LOGOUT
# =========================================================
@extend_schema(
    auth=[{"BearerAuth": []}],
    tags=["Logout"],
    summary="Logout",
    description=(
        "Logout the user by blacklisting the refresh token."
    ),
    request=LogoutSerializer,

    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Logout successful.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Logout successful.",
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class LogoutAPIView(CreateAPIView):
    serializer_class = LogoutSerializer
    def create(
        self,
        request,
        *args,
        **kwargs
    ):
        serializer = self.get_serializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )
        serializer.save()
        return Response(
            {
                "success": True,
                "message": "Logout successful.",
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# PROFILE
# =========================================================
@extend_schema(
    auth=[{"BearerAuth": []}],
    tags=["Accounts"],
    summary="Profile",
    description=(
        "Retrieve the profile details "
        "of the authenticated user."
    ),

    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Profile fetched successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Profile fetched successfully.",
                        "data": {
                            "id": 12,
                            "user_uuid": "b3f1c2d4-5678-4abc-9def-0123456789ab",
                            "firstName": "Ravi",
                            "lastName": "Kumar",
                            "role": "CUSTOMER",
                            "hasBusiness": False,
                            "businessVerified": False,
                            "businessStatus": None,
                            "email": "ravi.kumar@example.com",
                            "profileImage": "",
                            "phone": "9876543210",
                            "joinedate": "Jan 2026",
                            "addresses": [
                                {
                                    "add_uuid": "c4d5e6f7-8901-4abc-9def-123456789abc",
                                    "user_uuid": "b3f1c2d4-5678-4abc-9def-0123456789ab",
                                    "address_line": "221B Baker Street",
                                    "locality": "Indiranagar",
                                    "city": "Bengaluru",
                                    "state": "Karnataka",
                                    "pincode": "560038",
                                    "location": "",
                                    "address_type": "HOME",
                                    "is_default": True,
                                    "created_at": "2026-01-15T10:30:00Z",
                                    "updated_at": "2026-01-15T10:30:00Z",
                                },
                            ],
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class ProfileAPIView(APIView):
    permission_classes = [
        IsAuthenticated
    ]
    def get(self, request):
        user = request.user
        return Response(
            {
                "success": True,
                "message": (
                    "Profile fetched successfully."
                ),
                "data": {
                    "id": user.id,
                    "user_uuid": str(user.user_uuid),
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "role": user.role,
                    "hasBusiness": (
                        user.has_business
                    ),
                    "businessVerified": (
                        user.business_verified
                    ),
                    "businessStatus": (
                        user.business_applications.first().status
                        if user.business_applications.exists()
                        else None
                    ),
                    "email": user.email,
                    "profileImage": (
                        user.profile_picture.url
                        if user.profile_picture
                        else ""
                    ),
                    "phone": user.phone,
                    "joinedate": (
                        user.created_at.strftime(
                            "%b %Y"
                        )
                    ),
                    "addresses": AddressSerializer(
                        Address.objects.filter(
                            user=user
                        ),
                        many=True,
                    ).data,
                },
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# UPDATE PROFILE
# =========================================================
# =========================================================
# UPDATE PROFILE
# =========================================================
@extend_schema(
    tags=["Accounts"],
    summary="Update Profile",
    description=(
        "Update the authenticated user's profile. "
        "A new phone number requires OTP verification."
    ),
    request=UpdateProfileSerializer,
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description=(
                "Profile updated, or an OTP was sent because "
                "the phone number changed."
            ),
            examples=[
                OpenApiExample(
                    "Profile updated",
                    value={
                        "success": True,
                        "message": "Profile updated successfully.",
                        "data": {
                            "id": 12,
                            "user_uuid": "b3f1c2d4-5678-4abc-9def-0123456789ab",
                            "firstName": "Ravi",
                            "lastName": "Kumar",
                            "role": "CUSTOMER",
                            "hasBusiness": False,
                            "businessVerified": False,
                            "businessStatus": None,
                            "email": "ravi.kumar@example.com",
                            "profileImage": "",
                            "phone": "9876543210",
                            "joinedate": "Jan 2026",
                            "addresses": [],
                        },
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Phone change - OTP sent",
                    value={
                        "success": True,
                        "message": (
                            "OTP sent successfully. Please verify "
                            "the OTP to update your phone number."
                        ),
                        "data": {
                            "phone": "9123456780",
                            "otp_required": True,
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class UpdateProfileAPIView(APIView):
    permission_classes = [
        IsAuthenticated
    ]
    def post(
        self,
        request
    ):
        serializer = UpdateProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(
            raise_exception=True
        )
        new_phone = serializer.validated_data.get(
            "phone"
        )
        # -------------------------------------------------
        # PHONE NUMBER CHANGE
        # -------------------------------------------------
        if (
            new_phone
            and new_phone != request.user.phone
        ):
            if not OTPService.can_send_otp(
                new_phone
            ):
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Please wait 60 seconds "
                            "before requesting another OTP."
                        ),
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            otp = OTPService.create_otp(
                user=request.user,
                phone=new_phone,
            )
            print(
                f"\n{'=' * 50}\n"
                f"PHONE UPDATE OTP\n"
                f"User: {request.user.email}\n"
                f"Phone: {new_phone}\n"
                f"OTP: {otp}\n"
                f"Expires: 5 minutes\n"
                f"{'=' * 50}\n"
            )
            return Response(
                {
                    "success": True,
                    "message": (
                        "OTP sent successfully. "
                        "Please verify the OTP to update "
                        "your phone number."
                    ),
                    "data": {
                        "phone": new_phone,
                        "otp_required": True,
                    },
                },
                status=status.HTTP_200_OK,
            )
        # -------------------------------------------------
        # NORMAL PROFILE UPDATE
        # -------------------------------------------------
        serializer.save()
        request.user.refresh_from_db()
        return Response(
            {
                "success": True,
                "message": (
                    "Profile updated successfully."
                ),
                "data": {
                    "id": request.user.id,
                    "user_uuid": str(
                        request.user.user_uuid
                    ),
                    "firstName": (
                        request.user.first_name
                    ),
                    "lastName": (
                        request.user.last_name
                    ),
                    "role": request.user.role,
                    "hasBusiness": (
                        request.user.has_business
                    ),
                    "businessVerified": (
                        request.user.business_verified
                    ),
                    "businessStatus": (
                        request.user.business_applications.first().status
                        if request.user.business_applications.exists()
                        else None
                    ),
                    "email": request.user.email,
                    "profileImage": (
                        request.user.profile_picture.url
                        if request.user.profile_picture
                        else ""
                    ),
                    "phone": request.user.phone,
                    "joinedate": (
                        request.user.created_at.strftime(
                            "%b %Y"
                        )
                    ),
                    "addresses": AddressSerializer(
                        Address.objects.filter(
                            user=request.user
                        ),
                        many=True,
                    ).data,
                },
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# VERIFY PHONE UPDATE OTP
# =========================================================
@extend_schema(
    request=VerifyPhoneUpdateOTPSerializer,
    tags=["Accounts"],
    summary="Verify Phone Update OTP",
        responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Phone number updated successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Phone number updated successfully.",
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class VerifyPhoneUpdateOTPAPIView(APIView):
    permission_classes = [
        IsAuthenticated
    ]
    def post(
        self,
        request
    ):
        serializer = VerifyPhoneUpdateOTPSerializer(
            data=request.data,
            context={
                "request": request
            },
        )
        serializer.is_valid(
            raise_exception=True
        )
        user = request.user
        new_phone = serializer.validated_data["phone"]

        try:
            with transaction.atomic():
                user.phone = new_phone
                user.save(
                    update_fields=[
                        "phone",
                        "updated_at",
                    ]
                )
        except IntegrityError as exc:
            if "phone" in str(exc).lower():
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Phone number already exists."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise

        return Response(
            {
                "success": True,
                "message": (
                    "Phone number updated successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# LIST USER ADDRESSES
# =========================================================
@extend_schema(
    tags=["Address"],
    summary="List User Addresses",
    description=(
        "Retrieve all addresses of "
        "the authenticated user."
    ),
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Addresses fetched successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Addresses fetched successfully.",
                        "data": [
                            {
                                "add_uuid": "c4d5e6f7-8901-4abc-9def-123456789abc",
                                "user_uuid": "b3f1c2d4-5678-4abc-9def-0123456789ab",
                                "address_line": "221B Baker Street",
                                "locality": "Indiranagar",
                                "city": "Bengaluru",
                                "state": "Karnataka",
                                "pincode": "560038",
                                "location": "",
                                "address_type": "HOME",
                                "is_default": True,
                                "created_at": "2026-01-15T10:30:00Z",
                                "updated_at": "2026-01-15T10:30:00Z",
                            },
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class ListUserAddressesAPIView(APIView):
    permission_classes = [
        IsAuthenticated
    ]
    def get(
        self,
        request
    ):
        addresses = Address.objects.filter(
            user=request.user
        )
        serializer = AddressSerializer(
            addresses,
            many=True,
        )
        return Response(
            {
                "success": True,
                "message": (
                    "Addresses fetched successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# CREATE ADDRESS
# =========================================================
@extend_schema(
    tags=["Address"],
    summary="Add User Address",
    description=(
        "Add a new address for "
        "the authenticated user."
    ),
    request=AddressSerializer,
    responses={
        201: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Address added successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Address added successfully.",
                        "data": {
                            "add_uuid": "c4d5e6f7-8901-4abc-9def-123456789abc",
                            "user_uuid": "b3f1c2d4-5678-4abc-9def-0123456789ab",
                            "address_line": "221B Baker Street",
                            "locality": "Indiranagar",
                            "city": "Bengaluru",
                            "state": "Karnataka",
                            "pincode": "560038",
                            "location": "",
                            "address_type": "HOME",
                            "is_default": True,
                            "created_at": "2026-01-15T10:30:00Z",
                            "updated_at": "2026-01-15T10:30:00Z",
                        },
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Address limit reached",
                    value={
                        "success": False,
                        "message": "You can have a maximum of 5 addresses.",
                    },
                    response_only=True,
                    status_codes=["400"],
                ),
            ],
        ),
    },
)
class CreateUserAddressAPIView(APIView):
    permission_classes = [
        IsAuthenticated
    ]
    def post(
        self,
        request
    ):
        if Address.objects.filter(
            user=request.user
        ).count() >= 5:
            return Response(
                {
                    "success": False,
                    "message": (
                        "You can have a maximum "
                        "of 5 addresses."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = AddressSerializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True
        )
        serializer.save(
            user=request.user
        )
        return Response(
            {
                "success": True,
                "message": (
                    "Address added successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )
# =========================================================
# GET ADDRESS
# =========================================================
@extend_schema(
    tags=["Address"],
    summary="Get User Address",
    description=(
        "Retrieve a specific address "
        "of the authenticated user."
    ),
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Address fetched successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Address fetched successfully.",
                        "data": {
                            "add_uuid": "c4d5e6f7-8901-4abc-9def-123456789abc",
                            "user_uuid": "b3f1c2d4-5678-4abc-9def-0123456789ab",
                            "address_line": "221B Baker Street",
                            "locality": "Indiranagar",
                            "city": "Bengaluru",
                            "state": "Karnataka",
                            "pincode": "560038",
                            "location": "",
                            "address_type": "HOME",
                            "is_default": True,
                            "created_at": "2026-01-15T10:30:00Z",
                            "updated_at": "2026-01-15T10:30:00Z",
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },

)
class GetUserAddressAPIView(APIView):
    permission_classes = [
        IsAuthenticated
    ]
    def get(
        self,
        request,
        add_uuid
    ):
        address = get_object_or_404(
            Address,
            add_uuid=add_uuid,
            user=request.user,
        )
        serializer = AddressSerializer(
            address
        )
        return Response(
            {
                "success": True,
                "message": (
                    "Address fetched successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# UPDATE ADDRESS
# =========================================================
@extend_schema(
    tags=["Address"],
    summary="Update User Address",
    description=(
        "Update an existing address "
        "of the authenticated user."
    ),
    request=AddressSerializer,
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Address updated successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Address updated successfully.",
                        "data": {
                            "add_uuid": "c4d5e6f7-8901-4abc-9def-123456789abc",
                            "user_uuid": "b3f1c2d4-5678-4abc-9def-0123456789ab",
                            "address_line": "221B Baker Street",
                            "locality": "Indiranagar",
                            "city": "Bengaluru",
                            "state": "Karnataka",
                            "pincode": "560038",
                            "location": "",
                            "address_type": "WORK",
                            "is_default": False,
                            "created_at": "2026-01-15T10:30:00Z",
                            "updated_at": "2026-02-01T09:15:00Z",
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class UpdateUserAddressAPIView(APIView):
    permission_classes = [
        IsAuthenticated
    ]
    def post(
        self,
        request,
        add_uuid
    ):
        address = get_object_or_404(
            Address,
            add_uuid=add_uuid,
            user=request.user,
        )
        serializer = AddressSerializer(
            address,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(
            raise_exception=True
        )
        serializer.save()
        return Response(
            {
                "success": True,
                "message": (
                    "Address updated successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# DELETE ADDRESS
# =========================================================
@extend_schema(
    tags=["Address"],
    summary="Delete User Address",
    description=(
        "Delete an existing address "
        "of the authenticated user."
    ),
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Address deleted successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Address deleted successfully.",
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Not found",
                    value={
                        "success": False,
                        "message": "Address not found.",
                    },
                    response_only=True,
                    status_codes=["404"],
                ),
            ],
        ),
    },
)
class DeleteUserAddressAPIView(APIView):
    permission_classes = [
        IsAuthenticated
    ]
    def delete(
        self,
        request,
        add_uuid
    ):
        try:
            address = Address.objects.get(
                add_uuid=add_uuid,
                user=request.user,
            )
        except Address.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Address not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        address.delete()
        return Response(
            {
                "success": True,
                "message": (
                    "Address deleted successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# FORGOT PASSWORD
# =========================================================
class ForgotPasswordView(APIView):
    permission_classes = [
        AllowAny
    ]
    @extend_schema(
        auth=[],
        tags=["Login"],
        summary="Send password reset link",
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Password reset link sent successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "success": True,
                            "message": (
                                "Password reset link sent successfully."
                            ),
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def post(
        self,
        request
    ):
        serializer = ForgotPasswordSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )
        user = serializer.user
        reset_token = (
            AuthService.create_password_reset_token(
                user
            )
        )
        reset_link = (
            AuthService.get_password_reset_link(
                reset_token
            )
        )
        template = EmailTemplate.objects.get(
            name="PASSWORD_RESET_LINK"
        )
        html_message = render_to_string(
            "emails/base_email.html",
            {
                "subject": template.subject,
                "logo_url": "",
                "first_name": user.first_name,
                "message": template.message,
                "otp": "",
                "reset_link": reset_link,
                "additional_message": "",
            },
        )
        email_message = EmailMultiAlternatives(
            subject=template.subject,
            body=template.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email_message.attach_alternative(
            html_message,
            "text/html",
        )
        email_message.send(
            fail_silently=False
        )
        return Response(
            {
                "success": True,
                "message": (
                    "Password reset link sent successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# UNIFIED PASSWORD RESET
# =========================================================
class UnifiedPasswordResetView(APIView):
    permission_classes = [
        AllowAny
    ]
    @extend_schema(
        tags=["Login"],
        request=UnifiedPasswordResetSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description=(
                    "Reset link sent, or password reset completed, "
                    "depending on the request payload."
                ),
                examples=[
                    OpenApiExample(
                        "Reset link sent",
                        value={
                            "success": True,
                            "message": (
                                "Password reset link sent successfully."
                            ),
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Password reset",
                        value={
                            "success": True,
                            "message": "Password reset successfully.",
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def post(
        self,
        request
    ):
        serializer = UnifiedPasswordResetSerializer(
            data=request.data,
            context={
                "request": request
            },
        )
        serializer.is_valid(
            raise_exception=True
        )
        user = serializer.user
        # --------------------------------------------------
        # LOGGED-OUT USER
        # SEND RESET LINK
        # --------------------------------------------------
        if (
            not request.user.is_authenticated
            and serializer.validated_data.get(
                "email"
            )
            and not serializer.validated_data.get(
                "token"
            )
        ):
            reset_token = (
                AuthService.create_password_reset_token(
                    user
                )
            )
            reset_link = (
                f"{settings.FRONTEND_DOMAIN}/reset-password/"
                f"?user_uuid={user.user_uuid}"
                f"&token={reset_token.token}"
            )
            template = EmailTemplate.objects.get(
                name="PASSWORD_RESET_LINK"
            )
            subject = template.subject
            message = template.message.replace(
                "{{ first_name }}",
                user.first_name or "User"
            ).replace(
                "{{ reset_link }}",
                reset_link
            ).replace(
                "{{ expiry_minutes }}",
                "15"
            )
            html_message = render_to_string(
                "emails/base_email.html",
                {
                    "subject": subject,
                    "logo_url": "",
                    "first_name": (
                        user.first_name or "User"
                    ),
                    "message": message,
                    "otp": "",
                    "reset_link": reset_link,
                    "additional_message": "",
                },
            )
            email_message = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email_message.attach_alternative(
                html_message,
                "text/html",
            )
            email_message.send(
                fail_silently=False
            )
            return Response(
                {
                    "success": True,
                    "message": (
                        "Password reset link sent successfully."
                    ),
                },
                status=status.HTTP_200_OK,
            )
        # --------------------------------------------------
        # PASSWORD RESET
        # --------------------------------------------------
        new_password = (
            serializer.validated_data[
                "new_password"
            ]
        )
        AuthService.reset_password(
            user=user,
            new_password=new_password,
        )
        reset_token = getattr(
            serializer,
            "reset_token",
            None,
        )
        if reset_token:
            reset_token.is_used = True
            reset_token.save(
                update_fields=[
                    "is_used"
                ]
            )
        PasswordResetToken.objects.filter(
            user=user,
            is_used=False,
        ).update(
            is_used=True
        )
        return Response(
            {
                "success": True,
                "message": (
                    "Password reset successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# SIGNUP OTP - VERIFY
# =========================================================
@extend_schema(
    request=SignupVerifyOTPSerializer,
    tags=["SignUp"],
    summary="Verify Signup OTP",
    description=(
        "Verify the OTP sent to a new user's "
        "phone number."
    ),
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Signup successful.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Signup successful.",
                        "data": {
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "user": {
                                "id": 12,
                                "user_uuid": "b3f1c2d4-5678-4abc-9def-0123456789ab",
                                "first_name": "Ravi",
                                "last_name": "Kumar",
                                "email": "",
                                "phone": "9876543210",
                                "role": "CUSTOMER",
                                "profileImage": "",
                            },
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
class SignupVerifyOTPAPIView(APIView):
    authentication_classes = []
    permission_classes = [
        AllowAny
    ]
    def post(
        self,
        request
    ):
        serializer = SignupVerifyOTPSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )
        # -------------------------------------------------
        # Get BOTH phone and OTP from validated request data.
        #
        # phone is normalized by SignupVerifyOTPSerializer,
        # so the service receives the canonical 10-digit
        # Indian phone number.
        # -------------------------------------------------
        phone = serializer.validated_data[
            "phone"
        ]
        otp = serializer.validated_data[
            "otp"
        ]
        # -------------------------------------------------
        # Verify signup OTP against the SAME phone number.
        #
        # This prevents an OTP belonging to another phone
        # from being selected.
        # -------------------------------------------------
        user = AuthService.verify_phone_registration(
            phone=phone,
            otp=otp,
        )
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        return Response(
            {
                "success": True,
                "message": "Signup successful.",
                "data": {
                    "access": str(access),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "user_uuid": str(user.user_uuid),
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "phone": user.phone,
                        "role": user.role,
                        "profileImage": (
                            user.profile_picture.url
                            if user.profile_picture
                            else ""
                        )
                    },
                },
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# LOGIN OTP - SEND
# =========================================================
@extend_schema(
    request=LoginSendOTPSerializer,
    tags=["Login"],
    summary="Send Login OTP",
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="OTP sent successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "OTP sent successfully.",
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Rate limited",
                    value={
                        "success": False,
                        "message": (
                            "Please wait 60 seconds before "
                            "requesting another OTP."
                        ),
                    },
                    response_only=True,
                    status_codes=["429"],
                ),
            ],
        ),
    },
)
class LoginSendOTPAPIView(APIView):
    authentication_classes = []
    permission_classes = [
        AllowAny
    ]
    def post(
        self,
        request
    ):
        serializer = LoginSendOTPSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )
        user = serializer.user
        phone = serializer.validated_data[
            "phone"
        ]
        if not OTPService.can_send_otp(
            phone
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Please wait 60 seconds "
                        "before requesting another OTP."
                    ),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        otp = OTPService.create_otp(
            user=user,
            phone=phone,
        )
        print(
            f"\n{'=' * 50}\n"
            f"LOGIN OTP\n"
            f"Phone: {phone}\n"
            f"OTP: {otp}\n"
            f"Expires: 5 minutes\n"
            f"{'=' * 50}\n"
        )
        # -----------------------------------------------------
        # DEVELOPMENT MODE
        # -----------------------------------------------------
        logger.debug(
            "LOGIN OTP | Phone: %s | OTP: %s | Expires: 5 min",
            phone, otp,
        )
        return Response(
            {
                "success": True,
                "message": (
                    "OTP sent successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# LOGIN OTP - VERIFY
# =========================================================
@extend_schema(
    request=VerifyOTPSerializer,
    tags=["Login"],
    summary="Verify Login OTP",
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="OTP verified. Login successful.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "OTP verified. Login successful.",
                        "data": {
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "user": {
                                "id": 12,
                                "user_uuid": "b3f1c2d4-5678-4abc-9def-0123456789ab",
                                "first_name": "Ravi",
                                "last_name": "Kumar",
                                "email": "ravi.kumar@example.com",
                                "phone": "9876543210",
                                "role": "CUSTOMER",
                            },
                        },
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Invalid OTP",
                    value={
                        "success": False,
                        "message": "Invalid or expired OTP.",
                    },
                    response_only=True,
                    status_codes=["400"],
                ),
            ],
        ),
    },
)
class LoginVerifyOTPAPIView(APIView):
    authentication_classes = []
    permission_classes = [
        AllowAny
    ]
    def post(
        self,
        request
    ):
        serializer = VerifyOTPSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )
        phone = serializer.validated_data[
            "phone"
        ]
        otp = serializer.validated_data[
            "otp"
        ]
        try:
            user = CustomUser.objects.get(
                phone=phone
            )
        except CustomUser.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "User not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        success, message = (
            OTPService.verify_otp(
                user=user,
                phone=phone,
                otp=otp,
            )
        )
        if not success:
            return Response(
                {
                    "success": False,
                    "message": message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        refresh = RefreshToken.for_user(
            user
        )
        return Response(
            {
                "success": True,
                "message": (
                    "OTP verified. "
                    "Login successful."
                ),
                "data": {
                    "access": str(
                        refresh.access_token
                    ),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "user_uuid": str(user.user_uuid),
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "phone": user.phone,
                        "role": user.role,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )
# =========================================================
# SIGNUP COMPLETE
# =========================================================
class GoogleLoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    @extend_schema(
        tags=["Login"],
        summary="Google Login",
        request=GoogleLoginSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Google login successful.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "success": True,
                            "message": "Google login successful.",
                            "data": {
                                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                "user": {
                                    "id": 12,
                                    "user_uuid": "b3f1c2d4-5678-4abc-9def-0123456789ab",
                                    "email": "ravi.kumar@example.com",
                                    "first_name": "Ravi",
                                    "last_name": "Kumar",
                                    "profileImage": "",
                                },
                            },
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Invalid credential",
                        value={
                            "success": False,
                            "message": "Invalid Google credential.",
                        },
                        response_only=True,
                        status_codes=["401"],
                    ),
                ],
            ),
        },
    )
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credential = serializer.validated_data["credential"]
        try:
            google_user = id_token.verify_oauth2_token(
                credential,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError:
            return Response(
                {
                    "success": False,
                    "message": "Invalid Google credential.",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        google_sub = google_user.get("sub")
        email = google_user.get("email")
        first_name = google_user.get("given_name", "")
        last_name = google_user.get("family_name", "")
        picture = google_user.get("picture")
        email_verified = google_user.get(
            "email_verified",
            False,
        )
        if not google_sub:
            return Response(
                {
                    "success": False,
                    "message": "Google account ID is missing.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not email:
            return Response(
                {
                    "success": False,
                    "message": "Google account does not have an email.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not email_verified:
            return Response(
                {
                    "success": False,
                    "message": "Google email is not verified.",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        User = get_user_model()

        try:
            with transaction.atomic():
                # --------------------------------------------------
                # 1. Check whether this Google account already exists
                # --------------------------------------------------
                google_identity = (
                    GoogleIdentity.objects
                    .select_related("user")
                    .filter(google_sub=google_sub)
                    .first()
                )

                if google_identity:
                    user = google_identity.user
                else:
                    # ----------------------------------------------
                    # 2. Check whether the verified email already
                    #    belongs to an existing TodayFix user
                    # ----------------------------------------------
                    user = User.objects.filter(
                        email__iexact=email
                    ).first()

                    if user:
                        # Lock the existing user while linking Google.
                        user = (
                            User.objects
                            .select_for_update()
                            .get(pk=user.pk)
                        )

                        # Another simultaneous request may have
                        # created the Google identity after our first
                        # lookup, so check again before creating it.
                        google_identity = (
                            GoogleIdentity.objects
                            .filter(user=user)
                            .first()
                        )

                        if google_identity:
                            user = google_identity.user
                        else:
                            GoogleIdentity.objects.create(
                                user=user,
                                google_sub=google_sub,
                                google_email=email,
                            )
                    else:
                        # ------------------------------------------
                        # 3. Create a new TodayFix user and Google
                        #    identity in the same transaction.
                        # ------------------------------------------
                        user = User.objects.create(
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            is_verified=True,
                            is_active=True,
                        )
                        user.set_unusable_password()
                        user.save(
                            update_fields=["password"]
                        )

                        GoogleIdentity.objects.create(
                            user=user,
                            google_sub=google_sub,
                            google_email=email,
                        )

        except IntegrityError:
            # A simultaneous first-time Google request may have
            # created the user/Google identity first. Recover by
            # reading the account created by that request instead
            # of allowing the IntegrityError to become a 500.
            google_identity = (
                GoogleIdentity.objects
                .select_related("user")
                .filter(google_sub=google_sub)
                .first()
            )

            if google_identity:
                user = google_identity.user
            else:
                user = User.objects.filter(
                    email__iexact=email
                ).first()

                if not user:
                    raise

                google_identity = (
                    GoogleIdentity.objects
                    .filter(user=user)
                    .first()
                )

                if not google_identity:
                    raise
        # --------------------------------------------------
        # 4. Make sure the TodayFix account is active
        # --------------------------------------------------
        if not user.is_active:
            return Response(
                {
                    "success": False,
                    "message": "This account is inactive.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        # --------------------------------------------------
        # 5. Generate the SAME JWT used by existing auth
        # --------------------------------------------------
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "message": "Google login successful.",
                "data": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "user_uuid": str(user.user_uuid),
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "profileImage": (
                            user.profile_picture.url
                            if user.profile_picture
                            else ""
                        )
                    },
                },
            },
            status=status.HTTP_200_OK,
        )


# =========================================================
# PROFILE PICTURE - VIEW (STREAMED)
# =========================================================

class ProfilePictureViewAPIView(APIView):
    """
    Streams a user's profile picture directly, instead of a raw
    /media/ URL. Any logged-in user can view any other user's
    profile picture (e.g. customer viewing a business owner's
    photo) - just not anonymous/logged-out access.
    """

    permission_classes = [
        IsAuthenticated
    ]

    @extend_schema(
        tags=["Accounts"],
        summary="View a user's profile picture",
    )
    def get(self, request, user_uuid):

        user = get_object_or_404(
            CustomUser,
            user_uuid=user_uuid,
        )

        return serve_document_file(user.profile_picture)
