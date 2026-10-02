from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest import mock

import pytest
from django.db import connections
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.check_balance import check_balance_after_transaction
from accounts.models import AccountORM
from transactions.choices import CategoryChoices, TransactionStatusChoices
from transactions.models import LedgerEntriesORM, TransactionORM


TRANSFERS_URL = reverse("transactions:transfer-create")

ALICE = "alice@example.com"
BOB = "bob@example.com"

pytestmark = pytest.mark.django_db


def account_of(email: str) -> AccountORM:
    return AccountORM.objects.get(client__user__email=email)


def send(client: APIClient, receiver_account_number: str, amount: str):
    return client.post(
        TRANSFERS_URL,
        {"receiver_account_number": receiver_account_number, "amount": amount},
        format="json",
    )


def assert_nothing_changed():
    assert account_of(ALICE).balance == Decimal("10000.00")
    assert account_of(BOB).balance == Decimal("10000.00")
    assert not TransactionORM.objects.exists()
    # Only the two welcome bonuses.
    assert LedgerEntriesORM.objects.count() == 2


def run_concurrently(calls):
    barrier = Barrier(len(calls))

    def worker(call):
        try:
            barrier.wait(timeout=10)
            return call()
        finally:
            # Each thread opens its own DB connection.
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures = [pool.submit(worker, call) for call in calls]
        return [future.result(timeout=30) for future in futures]


@pytest.fixture
def alice(authorized_client) -> APIClient:
    return authorized_client(ALICE)


@pytest.fixture
def bob(authorized_client) -> APIClient:
    return authorized_client(BOB)


def test_transfer_requires_authentication(api_client: APIClient, bob):
    response = send(api_client, account_of(BOB).account_number, "100.00")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    ("amount", "fee"),
    [
        ("0.01", "5.00"),
        ("100.00", "5.00"),
        ("200.00", "5.00"),
        # 2.5% = 5.005, rounded half up to the cent.
        ("200.20", "5.01"),
        ("1000.00", "25.00"),
    ],
)
def test_transfer_moves_money_and_charges_fee(alice, bob, amount, fee):
    response = send(alice, account_of(BOB).account_number, amount)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["amount"] == amount
    assert body["fee"] == fee
    assert body["status"] == TransactionStatusChoices.SUCCESS

    sender = account_of(ALICE)
    receiver = account_of(BOB)
    assert sender.balance == Decimal("10000.00") - Decimal(amount) - Decimal(fee)
    assert receiver.balance == Decimal("10000.00") + Decimal(amount)

    transfer = TransactionORM.objects.get(pk=body["id"])
    assert transfer.sender == sender
    assert transfer.receiver == receiver
    assert transfer.amount == Decimal(amount)
    assert transfer.fee == Decimal(fee)

    entries = {
        (entry.account_id, entry.category, entry.amount)
        for entry in LedgerEntriesORM.objects.filter(transaction=transfer)
    }
    assert entries == {
        (sender.pk, CategoryChoices.TRANSFER, -Decimal(amount)),
        (sender.pk, CategoryChoices.FEE, -Decimal(fee)),
        (receiver.pk, CategoryChoices.TRANSFER, Decimal(amount)),
    }


def test_transfer_can_spend_whole_balance(alice, bob):
    # 9756.10 + 243.90 fee == 10000.00
    response = send(alice, account_of(BOB).account_number, "9756.10")

    assert response.status_code == status.HTTP_201_CREATED
    assert account_of(ALICE).balance == Decimal("0.00")
    assert account_of(BOB).balance == Decimal("19756.10")


@pytest.mark.parametrize("amount", ["9756.11", "10000.00", "50000.00"])
def test_transfer_rejects_insufficient_funds_including_fee(alice, bob, amount):
    response = send(alice, account_of(BOB).account_number, amount)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "amount" in response.json()
    assert_nothing_changed()


@pytest.mark.parametrize(
    "amount",
    ["0", "-5.00", "100.001", "500000.01", "abc", ""],
)
def test_transfer_rejects_invalid_amount(alice, bob, amount):
    response = send(alice, account_of(BOB).account_number, amount)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert_nothing_changed()


def test_transfer_rejects_own_account(alice, bob):
    response = send(alice, account_of(ALICE).account_number, "100.00")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert_nothing_changed()


def test_transfer_rejects_unknown_receiver(alice, bob):
    taken = {account_of(ALICE).account_number, account_of(BOB).account_number}
    unknown = next(
        number for number in ("0000000000", "0000000001", "0000000002")
        if number not in taken
    )

    response = send(alice, unknown, "100.00")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert_nothing_changed()


def test_transfer_rolls_back_when_it_fails_midway(alice, bob):
    alice.raise_request_exception = False

    # Balances are already saved by the time ledger entries are written.
    with mock.patch.object(
        LedgerEntriesORM.objects,
        "bulk_create",
        side_effect=RuntimeError("ledger write failed"),
    ):
        response = send(alice, account_of(BOB).account_number, "100.00")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert_nothing_changed()


def test_balances_match_ledger_after_transfers(alice, bob):
    alice_number = account_of(ALICE).account_number
    bob_number = account_of(BOB).account_number

    send(alice, bob_number, "100.00")
    send(bob, alice_number, "2500.50")
    send(alice, bob_number, "0.01")
    send(alice, bob_number, "50000.00")  # rejected: insufficient funds

    assert check_balance_after_transaction() == []

    AccountORM.objects.filter(account_number=bob_number).update(
        balance=Decimal("1.00")
    )
    mismatches = check_balance_after_transaction()
    assert [mismatch["account_number"] for mismatch in mismatches] == [bob_number]


@pytest.mark.django_db(transaction=True)
def test_concurrent_transfers_cannot_overdraw_account(alice, bob, authorized_client):
    # Two requests of 6000.00 (+150.00 fee) against a 10000.00 balance.
    second_alice = authorized_client(ALICE)
    bob_number = account_of(BOB).account_number

    responses = run_concurrently([
        lambda: send(alice, bob_number, "6000.00"),
        lambda: send(second_alice, bob_number, "6000.00"),
    ])

    assert sorted(response.status_code for response in responses) == [
        status.HTTP_201_CREATED,
        status.HTTP_400_BAD_REQUEST,
    ]
    assert account_of(ALICE).balance == Decimal("3850.00")
    assert account_of(BOB).balance == Decimal("16000.00")
    assert TransactionORM.objects.count() == 1
    assert check_balance_after_transaction() == []


@pytest.mark.django_db(transaction=True)
def test_concurrent_opposite_transfers_do_not_deadlock(authorized_client):
    pairs = 4
    alice_clients = [authorized_client(ALICE) for _ in range(pairs)]
    bob_clients = [authorized_client(BOB) for _ in range(pairs)]
    alice_number = account_of(ALICE).account_number
    bob_number = account_of(BOB).account_number

    responses = run_concurrently(
        [lambda c=client: send(c, bob_number, "100.00") for client in alice_clients]
        + [lambda c=client: send(c, alice_number, "100.00") for client in bob_clients]
    )

    assert all(
        response.status_code == status.HTTP_201_CREATED for response in responses
    )
    # Amounts cancel out; each side only pays 4 x 5.00 in fees.
    assert account_of(ALICE).balance == Decimal("9980.00")
    assert account_of(BOB).balance == Decimal("9980.00")
    assert check_balance_after_transaction() == []
