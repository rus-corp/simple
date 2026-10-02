from rest_framework_simplejwt.authentication import JWTAuthentication
from common.logging import user_id_var


class ContextJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            user_id_var.set(str(result[0].pk))
        return result