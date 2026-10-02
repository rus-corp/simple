from django.urls import path

from .views import ReadAccountApiView


app_name = "accounts"

urlpatterns = [
    path("account/", ReadAccountApiView.as_view(), name="account-detail"),
]
