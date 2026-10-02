import logging
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from django.db.models import F, Sum

from .models import AccountORM


logger = logging.getLogger(__name__)


class BalanceMismatch(TypedDict):
    id: UUID
    account_number: str
    balance: Decimal
    ledger_balance: Decimal
    difference: Decimal


def check_balance_after_transaction() -> list[BalanceMismatch]:
    "Function for checking balance by ledgers after transactions"

    logger.info("Balance check started: comparing account balances with ledger sums")
    mismatches = list(
        AccountORM.objects
        .annotate(ledger_balance=Sum("ledgers__amount", default=Decimal("0.00")))
        .exclude(balance=F("ledger_balance"))
        .annotate(difference=F("balance") - F("ledger_balance"))
        .order_by("pk")
        .values("id", "account_number", "balance", "ledger_balance", "difference")
    )
    for mismatch in mismatches:
        logger.error(
            "Balance mismatch account_id=%s balance=%s ledger_balance=%s difference=%s",
            mismatch["id"], mismatch["balance"],
            mismatch["ledger_balance"], mismatch["difference"],
        )
    if not mismatches:
        logger.info("Balance check passed: all balances match the ledger")
    return mismatches
