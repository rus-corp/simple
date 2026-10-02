from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import AccountORM


ACCOUNT_URL = reverse("accounts:account-detail")
TRANSFERS_URL = reverse("transactions:transfer-create")

pytestmark = pytest.mark.django_db


def test_balance_requires_authentication(api_client: APIClient):
    response = api_client.get(ACCOUNT_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_balance_returns_current_account_state(authorized_client):
    client = authorized_client("alice@example.com")

    response = client.get(ACCOUNT_URL)

    account = AccountORM.objects.get(client__user__email="alice@example.com")
    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "account_number": account.account_number,
        "balance": "10000.00",
        "currency": "EUR",
    }
    assert account.balance == Decimal("10000.00")


def test_balance_is_scoped_to_authorized_user(authorized_client):
    alice = authorized_client("alice@example.com")
    bob = authorized_client("bob@example.com")
    AccountORM.objects.filter(client__user__email="bob@example.com").update(
        balance=Decimal("42.50")
    )

    alice_account = alice.get(ACCOUNT_URL).data
    bob_account = bob.get(ACCOUNT_URL).data

    assert alice_account["balance"] == "10000.00"
    assert bob_account["balance"] == "42.50"
    assert alice_account["account_number"] != bob_account["account_number"]


def test_balance_reflects_transfer(authorized_client):
    alice = authorized_client("alice@example.com")
    bob = authorized_client("bob@example.com")
    bob_account_number = bob.get(ACCOUNT_URL).data["account_number"]

    transfer = alice.post(
        TRANSFERS_URL,
        {"receiver_account_number": bob_account_number, "amount": "100.00"},
        format="json",
    )

    assert transfer.status_code == status.HTTP_201_CREATED
    # Sender pays the amount plus the EUR 5 minimum fee.
    assert alice.get(ACCOUNT_URL).data["balance"] == "9895.00"
    assert bob.get(ACCOUNT_URL).data["balance"] == "10100.00"
