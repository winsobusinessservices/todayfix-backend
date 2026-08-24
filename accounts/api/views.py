from accounts.models import GoogleIdentity
from django.contrib.auth import get_user_model
from rest_framework.compat import requests
from accounts.api.serializers import GoogleLoginSerializer
import logging

from accounts.choices import UserRole
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
)

from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
)

from rest_framework_simplejwt.tokens import RefreshToken

from django.shortcuts import get_object_or_404
from django.conf import settings
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
                    "id": user.id,
                    "user_uuid": str(user.user_uuid),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
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
                        user.role == UserRole.BUSINESS
                    ),
                    "businessVerified": (
                        user.business_verified
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

@extend_schema(
    tags=["Accounts"],
    summary="Update Profile",
    description=(
        "Update the authenticated user's profile."
    ),
    request=UpdateProfileSerializer,
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
        )

        serializer.is_valid(
            raise_exception=True
        )

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
                    "user_uuid": str(request.user.user_uuid),
                    "firstName": (
                        request.user.first_name
                    ),
                    "lastName": (
                        request.user.last_name
                    ),
                    "role": request.user.role,
                    "hasBusiness": (
                        request.user.role
                        == UserRole.BUSINESS
                    ),
                    "businessVerified": (
                        request.user.business_verified
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
# LIST USER ADDRESSES
# =========================================================

@extend_schema(
    tags=["Address"],
    summary="List User Addresses",
    description=(
        "Retrieve all addresses of "
        "the authenticated user."
    ),
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
        200: AddressSerializer
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

            try:

                user = CustomUser.objects.get(
                    phone=f"+91{phone}"
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
                # Link Google identity to existing user
                GoogleIdentity.objects.create(
                    user=user,
                    google_sub=google_sub,
                    google_email=email,
                )

            else:
                # ------------------------------------------
                # 3. Create a new TodayFix user
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
                        "profile_image": picture,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )

    


