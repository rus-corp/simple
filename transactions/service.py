from decimal import Decimal
from uuid import UUID
from django.db import transaction
from django.conf import settings

from .models import LedgerEntriesORM
from accounts.models import AccountORM
from .choices import CategoryChoices


class WelcomeBonusService:
    @transaction.atomic
    def grant(
        self,
        *,
        account_id: UUID
    ) -> LedgerEntriesORM:
        account = (
            AccountORM.objects
            .select_for_update()
            .get(pk=account_id)
        )
        existing_bonus = (
            LedgerEntriesORM.objects
            .filter(
                account=account,
                category=CategoryChoices.WELCOME_BONUS
            )
            .first()
        )

        if existing_bonus is not None:
            return existing_bonus

        amount: Decimal = settings.WELCOME_BONUS_AMOUNT

        bonus = LedgerEntriesORM.objects.create(
            account=account,
            transaction=None,
            amount=amount,
            category=CategoryChoices.WELCOME_BONUS
        )
        account.balance += amount
        account.save(update_fields=['balance'])
        return bonus
