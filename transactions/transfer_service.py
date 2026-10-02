from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID
from accounts.models import AccountORM
from django.conf import settings
from django.db import transaction
from .models import TransactionORM, LedgerEntriesORM
from .errors import TransferError, InsufficientFunds
from accounts.errors import AccountNotFound
from .choices import TransactionStatusChoices, CategoryChoices

cents = settings.CENT



def calculate_transfer_fee(
    amount: Decimal
) -> Decimal:
    fee = max(
        amount * settings.TRANSFER_FEE_RATE,
        settings.MIN_TRANSFER_FEE
    )
    return fee.quantize(cents, rounding=ROUND_HALF_UP)


class TransferService:
    @transaction.atomic
    def execute(
        self,
        *,
        sender_id: UUID,
        receiver_id: UUID,
        amount: Decimal
    ) -> TransactionORM:
        if not amount.is_finite() or not Decimal('0') < amount:
            raise TransferError('Invalid transfer amount')

        if amount > settings.MAX_TRANSFER_AMOUNT:
            raise TransferError(
                f'Transfer amount must not exceed EUR {settings.MAX_TRANSFER_AMOUNT}'
            )
        
        if amount != amount.quantize(cents):
            raise TransferError('Amount must be in whole cents')
        
        if sender_id == receiver_id:
            raise TransferError('Cannot transfer to the same account')
        
        accounts = {
            account.pk: account
            for account in (
                AccountORM.objects
                .select_for_update()
                .filter(pk__in=[sender_id, receiver_id])
                .order_by("pk")
            )
        }

        if len(accounts) != 2:
            raise AccountNotFound()
        
        sender = accounts[sender_id]
        receiver = accounts[receiver_id]

        fee = calculate_transfer_fee(amount)
        total = amount + fee
        if sender.balance < total:
            raise InsufficientFunds(
                'Insufficient funds'
            )
        transfer = TransactionORM.objects.create(
            sender=sender,
            receiver=receiver,
            amount=amount,
            fee=fee,
            status=TransactionStatusChoices.SUCCESS
        )
        sender.balance -= total
        receiver.balance += amount

        sender.save(update_fields=['balance'])
        receiver.save(update_fields=['balance'])

        LedgerEntriesORM.objects.bulk_create([
            LedgerEntriesORM(
                account=sender,
                transaction=transfer,
                amount=-amount,
                category=CategoryChoices.TRANSFER
            ),
            LedgerEntriesORM(
                account=sender,
                transaction=transfer,
                amount=-fee,
                category=CategoryChoices.FEE
            ),
            LedgerEntriesORM(
                account=receiver,
                transaction=transfer,
                amount=amount,
                category=CategoryChoices.TRANSFER
            ),
        ])

        return transfer
