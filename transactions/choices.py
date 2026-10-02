from django.db import models


class CategoryChoices(models.TextChoices):
    WELCOME_BONUS = 'welcome_bonus'
    TRANSFER = 'transfer'
    FEE = 'fee'


class DirectionChoices(models.TextChoices):
    DEBIT = 'debit'
    CREDIT = 'credit'


class TransactionStatusChoices(models.TextChoices):
    PENDING = 'PENDING'
    PROCESS = 'PROCESS'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    CANCELED = 'CANCELED'
