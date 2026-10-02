import logging
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

logger = logging.getLogger(__name__)



def calculate_transfer_fee(
    amount: Decimal
) -> Decimal:
    fee = max(
        amount * settings.TRANSFER_FEE_RATE,
        settings.MIN_TRANSFER_FEE
    )
    return fee.quantize(cents, rounding=ROUND_HALF_UP)


class TransferService:
    "This class make money transfer in atomic transactions"
    @transaction.atomic
    def execute(
        self,
        *,
        sender_id: UUID,
        receiver_id: UUID,
        amount: Decimal
    ) -> TransactionORM:
        logger.info(
            "Transfer started sender_account_id=%s receiver_account_id=%s amount=%s",
            sender_id, receiver_id, amount,
        )

        if not amount.is_finite() or not Decimal('0') < amount:
            logger.warning("Transfer rejected: amount is not a positive number amount=%s", amount)
            raise TransferError('Invalid transfer amount')

        if amount > settings.MAX_TRANSFER_AMOUNT:
            logger.warning(
                "Transfer rejected: amount exceeds the limit amount=%s limit=%s",
                amount, settings.MAX_TRANSFER_AMOUNT,
            )
            raise TransferError(
                f'Transfer amount must not exceed EUR {settings.MAX_TRANSFER_AMOUNT}'
            )

        if amount != amount.quantize(cents):
            logger.warning("Transfer rejected: amount is not in whole cents amount=%s", amount)
            raise TransferError('Amount must be in whole cents')

        if sender_id == receiver_id:
            logger.warning(
                "Transfer rejected: sender and receiver are the same account account_id=%s",
                sender_id,
            )
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
            logger.warning(
                "Transfer rejected: account not found sender_account_id=%s receiver_account_id=%s",
                sender_id, receiver_id,
            )
            raise AccountNotFound()

        sender = accounts[sender_id]
        receiver = accounts[receiver_id]

        fee = calculate_transfer_fee(amount)
        total = amount + fee
        if sender.balance < total:
            logger.warning(
                "Transfer rejected: insufficient funds sender_account_id=%s "
                "amount=%s fee=%s required=%s available=%s",
                sender_id, amount, fee, total, sender.balance,
            )
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

        logger.info(
            "Transfer completed transfer_id=%s sender_account_id=%s receiver_account_id=%s "
            "amount=%s fee=%s debited=%s credited=%s",
            transfer.pk, sender_id, receiver_id, amount, fee, total, amount,
        )
        return transfer
