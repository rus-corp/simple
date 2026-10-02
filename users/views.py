from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import BaseThrottle, ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView



from clients.errors import EmailAlreadyExists


from clients.services import RegistrationClientService
from .serializers import RegisteredUserSerializer, RegisterSerializer


class LoginApiView(TokenObtainPairView):
    throttle_classes: list[type[BaseThrottle]] = [ScopedRateThrottle]
    throttle_scope: str = "auth_login"


class RefreshTokenApiView(TokenRefreshView):
    throttle_classes: list[type[BaseThrottle]] = [ScopedRateThrottle]
    throttle_scope: str = "auth_refresh"


class RegisterApiView(APIView):
    permission_classes: list[type[BasePermission]] = [AllowAny]
    authentication_classes: list[type[BaseAuthentication]] = []
    throttle_classes: list[type[BaseThrottle]] = [ScopedRateThrottle]
    throttle_scope: str = "auth_register"

    def post(
        self,
        request: Request,
    ) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = RegistrationClientService().execute(
                **serializer.validated_data,
            )
        except EmailAlreadyExists as error:
            raise ValidationError(
                {"email": ["Email already exists"]}
            ) from error

        return Response(
            RegisteredUserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )
