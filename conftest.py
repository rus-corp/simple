import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    # Throttle counters live in the cache and would leak between tests.
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def authorized_client(db):
    """Returns a client with the user's JWT, registering them through the API first."""

    def create(
        email: str,
        password: str = "Str0ng-Passw0rd!",
    ) -> APIClient:
        client = APIClient()
        credentials = {"email": email, "password": password}
        if not get_user_model().objects.filter(email=email).exists():
            client.post(reverse("users:register"), credentials, format="json")
        token = client.post(reverse("users:token"), credentials, format="json")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.data['access']}")
        return client

    return create
