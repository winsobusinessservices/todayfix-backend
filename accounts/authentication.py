from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):

    def authenticate(self, request):

        result = super().authenticate(request)

        if result is None:
            return None

        user, token = result

        if user.last_logout:
            token_time = token["iat"]

            if token_time < int(user.last_logout.timestamp()):
                raise AuthenticationFailed(
                    "Token expired. Please login again."
                )

        return user, token
    

    