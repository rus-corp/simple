from decimal import Decimal
from django.db import models
from common.models import UUIDModel
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator



class AccountORM(UUIDModel):
    client = models.OneToOneField(
        to='clients.ClientsORM',
        on_delete=models.PROTECT,
        related_name='account'
    )
    account_number = models.CharField(
        unique=True,
        max_length=10,
        verbose_name=_('Account number'),
        validators=[
            RegexValidator(
                regex=r"\A[0-9]{10}\Z",
                message="Account number must contain exactly 10 digits.",
            )
        ]
    )
    balance = models.DecimalField(
        verbose_name=_('Balance'),
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    account_number__regex=r"^[0-9]{10}$",
                ),
                name="account_number_10_digits",
            ),
            models.CheckConstraint(
                condition=models.Q(balance__gte=0),
                name="account_balance_non_negative",
            ),
        ]

    def __str__(self):
        return self.account_number