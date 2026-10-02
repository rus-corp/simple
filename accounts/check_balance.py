from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from django.db.models import F, Sum

from .models import AccountORM


class BalanceMismatch(TypedDict):
    id: UUID
    account_number: str
    balance: Decimal
    ledger_balance: Decimal
    difference: Decimal


def check_balance_after_transaction() -> list[BalanceMismatch]:
    "Function for checking balance by ledgers after transactions"
    
    return list(
        AccountORM.objects
        .annotate(ledger_balance=Sum("ledgers__amount", default=Decimal("0.00")))
        .exclude(balance=F("ledger_balance"))
        .annotate(difference=F("balance") - F("ledger_balance"))
        .order_by("pk")
        .values("id", "account_number", "balance", "ledger_balance", "difference")
    )