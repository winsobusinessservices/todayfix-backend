from django.urls import path

from .views import (
    RegisterUserAPIView,
    RegisterBusinessAPIView,
)

urlpatterns = [

    path(
        "register/user/",
        RegisterUserAPIView.as_view(),
        name="register-user",
    ),

    path(
        "register/business/",
        RegisterBusinessAPIView.as_view(),
        name="register-business",
    ),

]
