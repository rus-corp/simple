import logging
from decimal import Decimal
from uuid import UUID
from django.db import transaction
from django.conf import settings

from .models import LedgerEntriesORM
from accounts.models import AccountORM
from .choices import CategoryChoices


logger = logging.getLogger(__name__)


class WelcomeBonusService:
    "Add welcome bonus to new client"
    @transaction.atomic
    def grant(
        self,
        *,
        account_id: UUID
    ) -> LedgerEntriesORM:
        amount: Decimal = settings.WELCOME_BONUS_AMOUNT
        logger.info(
            "Welcome bonus grant started account_id=%s amount=%s",
            account_id, amount,
        )
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
            logger.warning(
                "Welcome bonus skipped: already granted account_id=%s entry_id=%s",
                account_id, existing_bonus.pk,
            )
            return existing_bonus

        bonus = LedgerEntriesORM.objects.create(
            account=account,
            transaction=None,
            amount=amount,
            category=CategoryChoices.WELCOME_BONUS
        )
        account.balance += amount
        account.save(update_fields=['balance'])
        logger.info(
            "Welcome bonus granted account_id=%s entry_id=%s amount=%s balance=%s",
            account_id, bonus.pk, amount, account.balance,
        )
        return bonus
