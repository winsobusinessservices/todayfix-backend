import email

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
)

from .serializers import (
    RegisterUserSerializer,
    RegisterBusinessSerializer,
    LoginSerializer,
    LogoutSerializer,
    UpdateProfileSerializer, 
    UnifiedPasswordResetSerializer,
    ForgotPasswordSerializer,
    AddressSerializer,
    VerifyEmailSerializer,
    
)

from accounts.services import AuthService

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.shortcuts import get_object_or_404

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny


from accounts.models import PasswordResetToken, EmailTemplate, Address

from django.conf import settings

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

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

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pending_registration = serializer.save()

        verification_link = (
            f"{settings.FRONTEND_DOMAIN}/verify-email/"
            f"?uuid={pending_registration.uuid}"
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
            "24",
        )

        html_message = render_to_string(
            "emails/base_email.html",
            {
                "subject": template.subject,
                "logo_url": settings.EMAIL_LOGO_URL,
                "first_name": pending_registration.first_name or "User",
                "message": message,
                "otp": "",
                "verification_link": verification_link,
                "additional_message": "",
            },
        )

        email = EmailMultiAlternatives(
            subject=template.subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[pending_registration.email],
        )

        email.attach_alternative(
            html_message,
            "text/html",
        )

        email.send(fail_silently=False)

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
            description="Email verified successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": (
                            "Email verified successfully. "
                            "Registration completed."
                        ),
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

        serializer.is_valid(raise_exception=True)

        uuid_value = serializer.validated_data["uuid"]
        token = serializer.validated_data["token"]

        user = AuthService.verify_email_registration(
            uuid_value=uuid_value,
            token=token,
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Email verified successfully. "
                    "Registration completed."
                ),
                "data": {
                    "id": user.id,
                    "uuid": str(user.uuid),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                },
            },
            status=status.HTTP_200_OK,
        )

@extend_schema(
    auth=[],
    tags=["Signup"],
    summary="Register Business",
    description="Registers a new business account.",
    request=RegisterBusinessSerializer,
)
class RegisterBusinessAPIView(CreateAPIView):
    """
    Register a business account.
    """


class RegisterBusinessAPIView(CreateAPIView):
    """
    Register a business account.
    """

    serializer_class = RegisterBusinessSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response(
            {
                "success": True,
                "message": "Business account created successfully.",
                "data": {
                    "refresh": str(refresh),
                    "access": str(access),
                    "id": user.id,
                    "uuid": str(user.uuid),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                },
            },
            status=status.HTTP_201_CREATED,
        )

@extend_schema(
    auth=[],
    tags=["Login"],
    summary="Login",
    description="Login using email and password.",
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(
            description="Login successful.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Login successful.",
                        "data": {
                            "id": 1,
                            "uuid": "550e8400-e29b-41d4-a716-446655440000",
                            "first_name": "Demo1",
                            "last_name": "User",
                            "email": "demo1@example.com",
                            "phone": "+919876543210",
                            "role": "USER",
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Validation Error",
            examples=[
                OpenApiExample(
                    "Invalid Credentials",
                    value={
                        "detail": [
                            "Invalid email or password."
                        ]
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Email Required",
                    value={
                        "email": [
                            "This field is required."
                        ]
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Password Required",
                    value={
                        "password": [
                            "This field is required."
                        ]
                    },
                    response_only=True,
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            "Login User",
            value={
                "email": "demo1@example.com",
                "password": "Password@123"
            },
            request_only=True,
        ),
    ],
)

class LoginAPIView(CreateAPIView):

    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response(
            {
                "success": True,
                "message": "Login successful.",
                "data": {
                    "access": str(access),
                    "refresh": str(refresh),
                    "id": user.id,
                    "uuid": str(user.uuid),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                    
                },
            },
            status=status.HTTP_200_OK,
        )

@extend_schema(
    auth=[{"BearerAuth": []}],
    tags=["Login"],
    summary="Logout",
    description="Logout the user by blacklisting the refresh token.",
    request=LogoutSerializer,
    responses={
        200: OpenApiResponse(
            description="Logout successful.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Logout successful."
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Invalid refresh token.",
            examples=[
                OpenApiExample(
                    "Invalid Token",
                    value={
                        "detail": "Invalid refresh token."
                    },
                    response_only=True,
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            "Logout",
            value={
                "refresh": "<refresh_token>"
            },
            request_only=True,
        ),
    ],
)
class LogoutAPIView(CreateAPIView):

    serializer_class = LogoutSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            {
                "success": True,
                "message": "Logout successful.",
            },
            status=status.HTTP_200_OK,
        )

@extend_schema(
    auth=[{"BearerAuth": []}],
    tags=["Accounts"],
    summary="Profile",
    description="Retrieve the profile details of the authenticated user.",
    responses={
        200: OpenApiResponse(
            description="Profile fetched successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Profile fetched successfully.",
                        "data": {
                            "id": 1,
                            "uuid": "550e8400-e29b-41d4-a716-446655440000",
                            "first_name": "Demo1",
                            "last_name": "User",
                            "email": "demo1@example.com",
                            "phone": "+919876543210",
                            "role": "USER",
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
        401: OpenApiResponse(
            description="Authentication credentials were not provided.",
        ),
    },
)
class ProfileAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user

        return Response(
            {
                "success": True,
                "message": "Profile fetched successfully.",
                "data": {
                    "id": request.user.id,
                    "firstName": request.user.first_name,
                    "lastName": request.user.last_name,
                    "role": request.user.role,
                    "hasBusiness": request.user.role == "BUSINESS",
                    "businessVerified": request.user.business_verified,
                    "email": request.user.email,
                    "profileImage": (
                        request.user.profile_picture.url
                        if request.user.profile_picture
                        else ""
                    ),
                "phone": request.user.phone,
                "joinedate": request.user.created_at.strftime("%b %Y"),
                "addresses": AddressSerializer(
                    Address.objects.filter(user=request.user),
                    many=True,
                ).data,
                },
            },
            status=status.HTTP_200_OK,
        )
    
@extend_schema(
    tags=["Accounts"],
    summary="Update Profile",
    description="Update the authenticated user's profile.",
    request=UpdateProfileSerializer,
    responses={
        200: OpenApiResponse(
            description="Profile updated successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Profile updated successfully.",
                        "data": {
                            "firstName": "",
                            "lastName": "",
                            "profileImage": "",
                            "phone": "",
                            "addresses": [],
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Validation Error",
        ),
        401: OpenApiResponse(
            description="Authentication credentials were not provided.",
        ),
    },
    examples=[
        OpenApiExample(
            "Update Profile",
            value={
                "firstName": "",
                "lastName": "",
                "profileImage": "",
                "phone": "",
                "addresses": [],
            },
            request_only=True,
        ),
    ],
)
class UpdateProfileAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = UpdateProfileSerializer(
            request.user,
            data=request.data,
            
        )

        serializer.is_valid(raise_exception=True)

        serializer.save()
        request.user.refresh_from_db()
        print(request.user.first_name)

        return Response(
            {
                "success": True,
                "message": "Profile updated successfully.",
                "data": {
                    "id": request.user.id,
                    "firstName": request.user.first_name,
                    "lastName": request.user.last_name,
                    "role": request.user.role,
                    "hasBusiness": request.user.role == "BUSINESS",
                    "businessVerified": request.user.business_verified,
                    "email": request.user.email,
                    "profileImage": (
                        request.user.profile_picture.url
                        if request.user.profile_picture
                        else ""
                    ),
                    "phone": request.user.phone,
                    "joinedate": request.user.created_at.strftime("%b %Y"),
                    "addresses": AddressSerializer(
                        Address.objects.filter(user=request.user),
                        many=True,
                    ).data,
                },
            },
            status=status.HTTP_200_OK,
        )

@extend_schema(
    tags=["Address"],
    summary="List User Addresses",
    description="Retrieve all addresses of the authenticated user.",
    responses={200: AddressSerializer},
)
class ListUserAddressesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = Address.objects.filter(user=request.user)

        serializer = AddressSerializer(
            addresses,
            many=True,
        )

        return Response(
            {
                "success": True,
                "message": "Addresses fetched successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Address"],
    summary="Add User Address",
    description="Add a new address for the authenticated user.",
    request=AddressSerializer,
    responses={201: AddressSerializer},
)
class CreateUserAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        if Address.objects.filter(user=request.user).count() >= 5:
            return Response(
                {
                    "success": False,
                    "message": "You can have a maximum of 5 addresses.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AddressSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        serializer.save(user=request.user)

        return Response(
            {
                "success": True,
                "message": "Address added successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Address"],
    summary="Get User Address",
    description="Retrieve a specific address of the authenticated user.",
    responses={200: AddressSerializer},
)
class GetUserAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, address_id):

        address = get_object_or_404(
            Address,
            id=address_id,
            user=request.user,
        )

        serializer = AddressSerializer(address)

        return Response(
            {
                "success": True,
                "message": "Address fetched successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Address"],
    summary="Update User Address",
    description="Update an existing address of the authenticated user.",
    request=AddressSerializer,
    responses={200: AddressSerializer},
)
class UpdateUserAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, address_id):

        address = Address.objects.get(
            id=address_id,
            user=request.user,
        )

        serializer = AddressSerializer(
            address,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            {
                "success": True,
                "message": "Address updated successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Address"],
    summary="Delete User Address",
    description="Delete an existing address of the authenticated user.",
    responses={200: OpenApiResponse},
)
class DeleteUserAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, address_id):

        try:
            address = Address.objects.get(
                id=address_id,
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
                "message": "Address deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )

#------Forgot Password View------#
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        auth=[],
        tags=["Login"],
        summary="Send password reset link",
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset link sent successfully."
            ),
            400: OpenApiResponse(
                description="Invalid email."
            ),
        },
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        user = serializer.user

        reset_token = AuthService.create_password_reset_token(
            user
        )

        reset_link = AuthService.get_password_reset_link(
            reset_token
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

        email = EmailMultiAlternatives(
            subject=template.subject,
            body=template.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )

        email.attach_alternative(
            html_message,
            "text/html",
        )

        email.send(fail_silently=False)

        return Response(
            {
                "success": True,
                "message": "Password reset link sent successfully.",
            },
            status=status.HTTP_200_OK,
        )

#---- Unified Password Reset View ---#
class UnifiedPasswordResetView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Login"],
        request=UnifiedPasswordResetSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset operation completed successfully."
            ),
            400: OpenApiResponse(
                description="Invalid password reset request."
            ),
        },
    )
    def post(self, request):
        serializer = UnifiedPasswordResetSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        user = serializer.user

        # --------------------------------------------------
        # LOGGED-OUT USER: Send reset link
        # --------------------------------------------------
        if (
            not request.user.is_authenticated
            and serializer.validated_data.get("email")
            and not serializer.validated_data.get("token")
        ):
            reset_token = AuthService.create_password_reset_token(user)

            reset_link = (
                f"{settings.FRONTEND_DOMAIN}/reset-password/"
                f"?uuid={user.uuid}"
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
                    "first_name": user.first_name or "User",
                    "message": message,
                    "otp": "",
                    "reset_link": reset_link,
                    "additional_message": "",
                },
            )

            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )

            email.attach_alternative(
                html_message,
                "text/html",
            )

            email.send(fail_silently=False)

            return Response(
                {
                    "success": True,
                    "message": "Password reset link sent successfully.",
                },
                status=status.HTTP_200_OK,
            )

        # --------------------------------------------------
        # PASSWORD RESET
        # --------------------------------------------------
        new_password = serializer.validated_data["new_password"]

        AuthService.reset_password(
            user=user,
            new_password=new_password,
        )

        # If reset was done using email link,
        # invalidate that token.
        reset_token = getattr(
            serializer,
            "reset_token",
            None,
        )

        if reset_token:
            reset_token.is_used = True
            reset_token.save(update_fields=["is_used"])

        # Invalidate any other unused reset tokens.
        PasswordResetToken.objects.filter(
            user=user,
            is_used=False,
        ).update(is_used=True)

        return Response(
            {
                "success": True,
                "message": "Password reset successfully.",
            },
            status=status.HTTP_200_OK,
        )
    
    