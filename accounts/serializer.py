from rest_framework import serializers

from .models import AccountORM


class AccountSerializer(serializers.ModelSerializer):
    currency = serializers.CharField(read_only=True, default="EUR")

    class Meta:
        model = AccountORM
        fields = ["account_number", "balance", "currency"]
        read_only_fields = fields
