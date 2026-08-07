from accounts.models import CustomUser
from accounts.choices import UserRole


class AuthService:

    @staticmethod
    def register_user(validated_data):

        validated_data["role"] = UserRole.USER
        validated_data["has_business"] = False
        validated_data["business_verified"] = False

        return CustomUser.objects.create_user(
            **validated_data
        )

    @staticmethod
    def register_business(validated_data):

        validated_data["role"] = UserRole.BUSINESS
        validated_data["has_business"] = True
        validated_data["business_verified"] = False

        return CustomUser.objects.create_user(
            **validated_data
        )
    