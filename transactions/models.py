from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import UUIDModel
from .choices import CategoryChoices, TransactionStatusChoices


class TransactionORM(UUIDModel):
    """Bussines transaction item; welcome bonuses are separate entries."""

    sender = models.ForeignKey(
        to="accounts.AccountORM",
        on_delete=models.PROTECT,
        related_name='outgoing_transactions',
    )
    receiver = models.ForeignKey(
        to="accounts.AccountORM",
        on_delete=models.PROTECT,
        related_name='incoming_transactions',
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    fee = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    status = models.CharField(
        max_length=16,
        choices=TransactionStatusChoices.choices,
        default=TransactionStatusChoices.PENDING,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="transaction_amount_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(fee__gte=0),
                name="transaction_fee_non_negative",
            ),
            models.CheckConstraint(
                condition=~models.Q(sender=models.F("receiver")),
                name="transaction_different_accounts",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=TransactionStatusChoices.values),
                name="transaction_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return str(self.pk)


class LedgerEntriesORM(UUIDModel):
    account = models.ForeignKey(
        to="accounts.AccountORM",
        on_delete=models.PROTECT,
        related_name='ledgers'
    )
    transaction = models.ForeignKey(
        TransactionORM,
        on_delete=models.PROTECT,
        related_name='ledgers',
        null=True,
        blank=True
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    category = models.CharField(
        max_length=16,
        choices=CategoryChoices.choices,
        blank=False,
        null=False
    )
    created_at = models.DateTimeField(
        verbose_name=_("Created at"),
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Ledger'
        verbose_name_plural = 'Ledgers'
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(amount=0),
                name="ledger_amount_non_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(category__in=CategoryChoices.values),
                name="ledger_category_valid",
            ),
            models.UniqueConstraint(
                fields=["account"],
                condition=models.Q(category=CategoryChoices.WELCOME_BONUS),
                name="ledger_one_welcome_bonus_per_account",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.pk}: {self.amount:+.2f}"