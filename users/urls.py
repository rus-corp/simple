from django.urls import path
from .views import LoginApiView, RefreshTokenApiView, RegisterApiView


app_name = "users"


urlpatterns = [
    path('token/', LoginApiView.as_view(), name='token'),
    path('token/refresh/', RefreshTokenApiView.as_view(), name='token_refresh'),
    path('register/', RegisterApiView.as_view(), name='register')
]
