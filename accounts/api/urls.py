from django.urls import path

from .views import (
    RegisterUserAPIView,
    LoginAPIView,
    LogoutAPIView,
    ProfileAPIView,
    ResetPasswordLinkView,
    UpdateProfileAPIView,
    ForgotPasswordView,
    VerifyPasswordResetOTPView,
    ResetPasswordView,
    PasswordResetLinkView,
)


urlpatterns = [

    path(
        "register/user/",
        RegisterUserAPIView.as_view(),
        name="register-user",
    ),

    path(
        "login/",
        LoginAPIView.as_view(),
        name="login",
    ),

    path(
        "logout/",
        LogoutAPIView.as_view(),
        name="logout",
    ),

    path(
        "profile/",
        ProfileAPIView.as_view(),
        name="profile",
    ),

    path(
        "profile/update/",
        UpdateProfileAPIView.as_view(),
        name="update-profile",
    ),

    path(
        "forgot-password/",
        ForgotPasswordView.as_view(),
        name="forgot-password",
    ),

    path(
        "forgot-password/verify-otp/",
        VerifyPasswordResetOTPView.as_view(),
        name="verify-password-reset-otp",
    ),

    path(
        "forgot-password/reset/",
        ResetPasswordView.as_view(),
        name="reset-password",
    ),

    path(
        "forgot-password/link/",
        PasswordResetLinkView.as_view(),
        name="password-reset-link",
    ),

    path(
        "forgot-password/reset-link/",
        ResetPasswordLinkView.as_view(),
        name="reset-password-link",
    ),
    
]







