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
    ResetPasswordLinkSerializer,
    UpdateProfileSerializer,
    VerifyPasswordResetOTPSerializer,
    ForgotPasswordSerializer, 
    ResetPasswordSerializer
)

from accounts.services import AuthService

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny


from .serializers import PasswordResetLinkSerializer
from accounts.models import PasswordResetToken, PasswordResetOTP

from django.core.mail import send_mail
from django.conf import settings

@extend_schema(
    auth=[],
    tags=["SignUp"],
    summary="Register User",
    description="Registers a new user with role USER.",
    request=RegisterUserSerializer,
    responses={
        201: OpenApiResponse(
            description="User registered successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "User registered successfully.",
                        "data": {
                            "id": 1,
                            "uuid": "550e8400-e29b-41d4-a716-446655440000",
                            "first_name": "John",
                            "last_name": "  Doe",
                            "email": "john@example.com",
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
                    "Passwords do not match",
                    value={
                        "confirm_password": [
                            "Passwords do not match."
                        ]
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Email already exists",
                    value={
                        "email": [
                            "A user with this email already exists."
                        ]
                    },
                    response_only=True,
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            "Register User",
            value={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone": "+919876543210",
                "password": "Password@123",
                "confirm_password": "Password@123",
            },
            request_only=True,
        ),
    ],
)

class RegisterUserAPIView(CreateAPIView):
    """
    Register a normal user.
    """

    serializer_class = RegisterUserSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response(
            {
                "success": True,
                "message": "User registered successfully.",
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
            status=status.HTTP_201_CREATED,
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
                "addresses": [],
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
                    "addresses": [],
                },
            },
            status=status.HTTP_200_OK,
        )
    
#====Forgot Password View====#
@extend_schema(
    request=ForgotPasswordSerializer,
)
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset OTP sent successfully."
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

        reset_otp = serializer.save()

        send_mail(
            subject="TodayFix Password Reset OTP",
            message=(
                f"Your TodayFix password reset OTP is: "
                f"{reset_otp.otp}\n\n"
                "This OTP is valid for 5 minutes."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[
                serializer.user.email,
            ],
            fail_silently=False,
        )

        return Response(
            {
                "success": True,
                "message": "Password reset OTP sent successfully.",
            },
            status=status.HTTP_200_OK,
        )

#---- Password Reset Link View ---#
class PasswordResetLinkView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=PasswordResetLinkSerializer,
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
        serializer = PasswordResetLinkSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        user = serializer.user

        reset_token = AuthService.create_password_reset_token(
            user
        )

        reset_link = (
            f"http://localhost:3000/reset-password/"
            f"?token={reset_token.token}"
        )

        send_mail(
            subject="TodayFix Password Reset",
            message=(
                "Use the following link to reset your "
                "TodayFix password:\n\n"
                f"{reset_link}\n\n"
                "This link is valid for 15 minutes."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response(
            {
                "success": True,
                "message": "Password reset link sent successfully.",
            },
            status=status.HTTP_200_OK,
        )

#---- Reset Password Link View ---#
class ResetPasswordLinkView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ResetPasswordLinkSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset successfully."
            ),
            400: OpenApiResponse(
                description="Invalid or expired reset token."
            ),
        },
    )
    def post(self, request):
        serializer = ResetPasswordLinkSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        reset_token = serializer.validated_data["reset_token"]
        password = serializer.validated_data["password"]

        user = reset_token.user

        # Set the new password securely
        user.set_password(password)
        user.save()

        # Invalidate the reset token
        reset_token.is_used = True
        reset_token.save(update_fields=["is_used"])

        return Response(
            {
                "success": True,
                "message": "Password reset successfully.",
            },
            status=status.HTTP_200_OK,
        )
    
#---- Verify Password Reset OTP View ---#
class VerifyPasswordResetOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=VerifyPasswordResetOTPSerializer,
        responses={
            200: OpenApiResponse(
                description="OTP verified successfully."
            ),
            400: OpenApiResponse(
                description="Invalid or expired OTP."
            ),
        },
    )
    def post(self, request):
        serializer = VerifyPasswordResetOTPSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        reset_otp = serializer.validated_data["reset_otp"]
        user = serializer.validated_data["user"]

        # Mark OTP as used
        reset_otp.is_used = True
        reset_otp.save(update_fields=["is_used"])

        reset_token = AuthService.create_password_reset_token(user)
        

        return Response(
            {
                "success": True,
                "message": "OTP verified successfully.",
                "data": {
                    "reset_token": reset_token.token,
                },
            },
            status=status.HTTP_200_OK,
        ) 

#---- Reset Password View ---#
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset successfully."
            ),
            400: OpenApiResponse(
                description="Invalid reset token or password."
            ),
        },
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        reset_token = serializer.validated_data["reset_token"]
        new_password = serializer.validated_data["new_password"]

        # Change the password through AuthService
        AuthService.reset_password(
            user=user,
            new_password=new_password,
        )

        # Make the reset token unusable
        reset_token.is_used = True
        reset_token.save(update_fields=["is_used"])

        # Invalidate any remaining OTPs
        PasswordResetOTP.objects.filter(
            user=user,
            is_used=False,
        ).update(is_used=True)

        # Invalidate any other unused reset tokens
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



    