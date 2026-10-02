from decimal import Decimal
from django.conf import settings
from rest_framework import serializers

from .choices import DirectionChoices
from .models import LedgerEntriesORM


class CreateTransferSerializer(serializers.Serializer):
    receiver_account_number = serializers.RegexField(
        regex=r"\A[0-9]{10}\Z",
    )
    amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=settings.MAX_TRANSFER_AMOUNT,
    )


class TransactionHistorySerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField(source="created_at", read_only=True)
    transfer_id = serializers.UUIDField(
        source="transaction_id", read_only=True, allow_null=True,
    )

    def get_amount(self, entry):
        return f"{abs(entry.amount):.2f}"

    def get_type(self, entry):
        return DirectionChoices.DEBIT if entry.amount < 0 else DirectionChoices.CREDIT

    class Meta:
        model = LedgerEntriesORM
        fields = ["id", "amount", "type", "category", "timestamp", "transfer_id"]
        read_only_fields = fields


class TransactionFiltersSerializer(serializers.Serializer):
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start = attrs.get("from_date")
        end = attrs.get("to_date")
        if start and end and start > end:
            raise serializers.ValidationError("'from' must not be later than 'to'.")
        return attrs
