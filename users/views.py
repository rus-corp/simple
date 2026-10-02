import logging

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
from common.logging import mask_email


from clients.services import RegistrationClientService
from .serializers import RegisteredUserSerializer, RegisterSerializer


logger = logging.getLogger(__name__)


def requested_email(request: Request) -> str:
    data = request.data
    return mask_email(data.get("email") if isinstance(data, dict) else None)


class LoginApiView(TokenObtainPairView):
    throttle_classes: list[type[BaseThrottle]] = [ScopedRateThrottle]
    throttle_scope: str = "auth_login"

    def post(self, request: Request, *args, **kwargs) -> Response:
        email = requested_email(request)
        logger.info("Login requested email=%s", email)
        response = super().post(request, *args, **kwargs)
        logger.info("Login succeeded, tokens issued email=%s", email)
        return response


class RefreshTokenApiView(TokenRefreshView):
    throttle_classes: list[type[BaseThrottle]] = [ScopedRateThrottle]
    throttle_scope: str = "auth_refresh"

    def post(self, request: Request, *args, **kwargs) -> Response:
        logger.info("Token refresh requested")
        response = super().post(request, *args, **kwargs)
        logger.info("Token refresh succeeded, new access token issued")
        return response


class RegisterApiView(APIView):
    permission_classes: list[type[BasePermission]] = [AllowAny]
    authentication_classes: list[type[BaseAuthentication]] = []
    throttle_classes: list[type[BaseThrottle]] = [ScopedRateThrottle]
    throttle_scope: str = "auth_register"

    def post(
        self,
        request: Request,
    ) -> Response:
        logger.info("Registration requested email=%s", requested_email(request))
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
