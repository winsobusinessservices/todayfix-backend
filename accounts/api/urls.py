from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterUserAPIView,
    VerifyEmailAPIView,
    LoginAPIView,
    LogoutAPIView,
    ProfileAPIView,
    UpdateProfileAPIView,

    ListUserAddressesAPIView,
    CreateUserAddressAPIView,
    GetUserAddressAPIView,
    UpdateUserAddressAPIView,
    DeleteUserAddressAPIView,

    ForgotPasswordView,
    UnifiedPasswordResetView,

    
    SignupVerifyOTPAPIView,

    LoginSendOTPAPIView,
    LoginVerifyOTPAPIView,

    
)


urlpatterns = [

    # =====================================================
    # SIGNUP
    # =====================================================

    path(
        "signup/register/",
        RegisterUserAPIView.as_view(),
        name="register-user",
    ),

    path(
        "signup/verify-email/",
        VerifyEmailAPIView.as_view(),
        name="verify-email",
    ),


    path(
        "signup/verify-otp/",
        SignupVerifyOTPAPIView.as_view(),
        name="signup-verify-otp",
    ),

    

    # =====================================================
    # LOGIN
    # =====================================================

    path(
        "login/",
        LoginAPIView.as_view(),
        name="login",
    ),

    path(
        "login/send-otp/",
        LoginSendOTPAPIView.as_view(),
        name="login-send-otp",
    ),

    path(
        "login/verify-otp/",
        LoginVerifyOTPAPIView.as_view(),
        name="login-verify-otp",
    ),

    # =====================================================
    # TOKEN
    # =====================================================

    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
    # =====================================================
    # LOGOUT
    # =====================================================

    path(
        "logout/",
        LogoutAPIView.as_view(),
        name="logout",
    ),

    # =====================================================
    # PROFILE
    # =====================================================

    path(
        "profile/",
        ProfileAPIView.as_view(),
        name="profile",
    ),

    path(
        "profile/update/",
        UpdateProfileAPIView.as_view(),
        name="profile-update",
    ),

    # =====================================================
    # ADDRESS
    # =====================================================

    path(
        "addresses/",
        ListUserAddressesAPIView.as_view(),
        name="address-list",
    ),

    path(
        "addresses/create/",
        CreateUserAddressAPIView.as_view(),
        name="address-create",
    ),

    path(
        "addresses/<uuid:add_uuid>/",
        GetUserAddressAPIView.as_view(),
        name="address-detail",
    ),

    path(
        "addresses/<uuid:add_uuid>/update/",
        UpdateUserAddressAPIView.as_view(),
        name="address-update",
    ),

    path(
        "addresses/<uuid:add_uuid>/delete/",
        DeleteUserAddressAPIView.as_view(),
        name="address-delete",
    ),

    # =====================================================
    # PASSWORD
    # =====================================================

    path(
        "password/forgot/",
        ForgotPasswordView.as_view(),
        name="forgot-password",
    ),

    path(
        "password/reset/",
        UnifiedPasswordResetView.as_view(),
        name="password-reset",
    ),
]



