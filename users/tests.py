from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import AccountORM
from transactions.choices import CategoryChoices
from transactions.models import LedgerEntriesORM


User = get_user_model()

REGISTER_URL = reverse("users:register")
LOGIN_URL = reverse("users:token")
ACCOUNT_URL = reverse("accounts:account-detail")
TRANSACTIONS_URL = reverse("transactions:transaction-list")

EMAIL = "alice@example.com"
PASSWORD = "Str0ng-Passw0rd!"

pytestmark = pytest.mark.django_db


def register(
    api_client: APIClient,
    email: str = EMAIL,
    password: str = PASSWORD,
):
    return api_client.post(
        REGISTER_URL,
        {"email": email, "password": password},
        format="json",
    )


def login(
    api_client: APIClient,
    email: str = EMAIL,
    password: str = PASSWORD,
):
    return api_client.post(
        LOGIN_URL,
        {"email": email, "password": password},
        format="json",
    )


def test_register_creates_user_account_and_welcome_bonus(api_client: APIClient):
    response = register(api_client)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["email"] == EMAIL
    assert "password" not in response.data

    user = User.objects.get(email=EMAIL)
    assert str(user.pk) == response.data["id"]
    assert user.password != PASSWORD
    assert user.check_password(PASSWORD)

    account = AccountORM.objects.get(client__user=user)
    assert len(account.account_number) == 10
    assert account.account_number.isdigit()
    assert account.balance == Decimal("10000.00")

    bonus = LedgerEntriesORM.objects.get(account=account)
    assert bonus.amount == Decimal("10000.00")
    assert bonus.category == CategoryChoices.WELCOME_BONUS
    assert bonus.transaction is None


def test_register_rejects_duplicate_email(api_client: APIClient):
    register(api_client)

    response = register(api_client, email=EMAIL.upper())

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data
    assert User.objects.count() == 1
    assert AccountORM.objects.count() == 1
    assert LedgerEntriesORM.objects.count() == 1


def test_register_rejects_weak_password(api_client: APIClient):
    response = register(api_client, password="12345678")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password" in response.data
    assert not User.objects.exists()
    assert not AccountORM.objects.exists()
    assert not LedgerEntriesORM.objects.exists()


def test_login_returns_tokens(api_client: APIClient):
    register(api_client)

    response = login(api_client)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["access"]
    assert response.data["refresh"]


def test_login_rejects_wrong_password(api_client: APIClient):
    register(api_client)

    response = login(api_client, password="wrong-password")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "access" not in response.data


def test_registered_user_sees_welcome_bonus_with_token(api_client: APIClient):
    register(api_client)
    access = login(api_client).data["access"]

    assert api_client.get(ACCOUNT_URL).status_code == status.HTTP_401_UNAUTHORIZED

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    account = api_client.get(ACCOUNT_URL)
    transactions = api_client.get(TRANSACTIONS_URL)

    assert account.status_code == status.HTTP_200_OK
    assert account.data["balance"] == "10000.00"

    assert transactions.status_code == status.HTTP_200_OK
    assert transactions.data["count"] == 1
    entry = transactions.data["results"][0]
    assert entry["amount"] == "10000.00"
    assert entry["type"] == "credit"
    assert entry["category"] == CategoryChoices.WELCOME_BONUS
    assert entry["timestamp"]
