from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import AccountORM
from transactions.choices import CategoryChoices
from transactions.models import LedgerEntriesORM


ACCOUNT_URL = reverse("accounts:account-detail")
TRANSFERS_URL = reverse("transactions:transfer-create")
TRANSACTIONS_URL = reverse("transactions:transaction-list")

pytestmark = pytest.mark.django_db


def transaction_url(pk) -> str:
    return reverse("transactions:transaction-detail", kwargs={"pk": pk})


def transfer(sender: APIClient, receiver: APIClient, amount: str):
    return sender.post(
        TRANSFERS_URL,
        {
            "receiver_account_number": receiver.get(ACCOUNT_URL).data["account_number"],
            "amount": amount,
        },
        format="json",
    )


def add_entry(
    account: AccountORM,
    amount: str,
    created_at: datetime,
) -> LedgerEntriesORM:
    entry = LedgerEntriesORM.objects.create(
        account=account,
        amount=Decimal(amount),
        category=CategoryChoices.TRANSFER,
    )
    # created_at is auto_now_add, so it can only be backdated with an update.
    LedgerEntriesORM.objects.filter(pk=entry.pk).update(created_at=created_at)
    return entry


def test_transactions_require_authentication(api_client: APIClient):
    list_response = api_client.get(TRANSACTIONS_URL)
    detail_response = api_client.get(transaction_url(uuid4()))

    assert list_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert detail_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_returns_all_user_transactions(authorized_client):
    alice = authorized_client("alice@example.com")
    bob = authorized_client("bob@example.com")
    transfer(alice, bob, "100.00")

    alice_response = alice.get(TRANSACTIONS_URL)
    bob_response = bob.get(TRANSACTIONS_URL)

    assert alice_response.status_code == status.HTTP_200_OK
    alice_items = alice_response.json()["results"]
    assert sorted((item["amount"], item["type"]) for item in alice_items) == [
        ("100.00", "debit"),
        ("10000.00", "credit"),
        ("5.00", "debit"),
    ]

    bob_items = bob_response.json()["results"]
    assert sorted((item["amount"], item["type"]) for item in bob_items) == [
        ("100.00", "credit"),
        ("10000.00", "credit"),
    ]

    for item in alice_items + bob_items:
        entry = LedgerEntriesORM.objects.get(pk=item["id"])
        assert datetime.fromisoformat(item["timestamp"]) == entry.created_at


@pytest.mark.parametrize(
    ("query", "expected_amounts"),
    [
        ({}, ["4.00", "3.00", "2.00", "1.00", "10000.00"]),
        ({"from": "2026-09-01", "to": "2026-09-28"}, ["3.00", "2.00", "1.00"]),
        ({"from": "2026-09-15"}, ["4.00", "3.00", "2.00"]),
        ({"to": "2026-09-01"}, ["1.00", "10000.00"]),
        ({"from": "2026-09-15", "to": "2026-09-15"}, ["2.00"]),
        ({"from": "2026-11-01"}, []),
    ],
)
def test_list_filters_by_date_range(authorized_client, query, expected_amounts):
    alice = authorized_client("alice@example.com")
    account = AccountORM.objects.get(client__user__email="alice@example.com")
    LedgerEntriesORM.objects.filter(account=account).update(
        created_at=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
    )
    # Both boundaries of the 09-01..09-28 range fall on the edge of the day.
    add_entry(account, "1.00", datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc))
    add_entry(account, "2.00", datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc))
    add_entry(account, "3.00", datetime(2026, 9, 28, 23, 59, 59, tzinfo=timezone.utc))
    add_entry(account, "4.00", datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc))

    response = alice.get(TRANSACTIONS_URL, query)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["count"] == len(expected_amounts)
    assert [item["amount"] for item in body["results"]] == expected_amounts


@pytest.mark.parametrize(
    "query",
    [
        {"from": "not-a-date"},
        {"to": "2026-13-40"},
        {"from": "2026-09-28", "to": "2026-09-01"},
    ],
)
def test_list_rejects_invalid_date_range(authorized_client, query):
    alice = authorized_client("alice@example.com")

    response = alice.get(TRANSACTIONS_URL, query)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_detail_returns_single_transaction(authorized_client):
    alice = authorized_client("alice@example.com")
    bob = authorized_client("bob@example.com")
    transfer(alice, bob, "1000.00")
    fee = LedgerEntriesORM.objects.get(category=CategoryChoices.FEE)

    response = alice.get(transaction_url(fee.pk))

    assert response.status_code == status.HTTP_200_OK
    item = response.json()
    assert item["amount"] == "25.00"
    assert item["type"] == "debit"
    assert datetime.fromisoformat(item["timestamp"]) == fee.created_at


def test_detail_hides_other_users_transaction(authorized_client):
    alice = authorized_client("alice@example.com")
    bob = authorized_client("bob@example.com")
    transfer(alice, bob, "100.00")
    alice_debit = LedgerEntriesORM.objects.get(
        category=CategoryChoices.TRANSFER,
        amount__lt=0,
    )

    response = bob.get(transaction_url(alice_debit.pk))

    assert response.status_code == status.HTTP_404_NOT_FOUND
