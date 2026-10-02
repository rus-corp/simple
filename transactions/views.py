import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from .transfer_service import TransferService
from .serializers import (
    CreateTransferSerializer,
    TransactionFiltersSerializer,
)
from .choices import DirectionChoices
from accounts.models import AccountORM
from .errors import InsufficientFunds, TransferError
from accounts.errors import AccountNotFound
from .pagination import TransactionPagination
from .mixin import UserTransactionsMixin


logger = logging.getLogger(__name__)



class CreateTransferApiView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logger.info("Transfer requested")
        serializer = CreateTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        logger.info(
            "Transfer request is valid receiver_account_number=%s amount=%s",
            data['receiver_account_number'], data['amount'],
        )

        sender = get_object_or_404(
            AccountORM,
            client__user=request.user
        )
        receiver = get_object_or_404(
            AccountORM,
            account_number=data['receiver_account_number']
        )

        try:
            transfer = TransferService().execute(
                sender_id=sender.pk,
                receiver_id=receiver.pk,
                amount=data['amount']
            )
        except InsufficientFunds as error:
            raise ValidationError(
                {'amount': ['Insufficient funds, including the fee.']}
            ) from error
        except TransferError as error:
            raise ValidationError(
                {'detail': str(error)}
            ) from error
        except AccountNotFound as error:
            raise NotFound('Account not found') from error
        return Response(
            {
                "id": str(transfer.pk),
                "amount": str(transfer.amount),
                "fee": str(transfer.fee),
                "status": transfer.status,
                "type": DirectionChoices.DEBIT,
                "created_at": transfer.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED
        )



class ReadTransactionsApiView(
    UserTransactionsMixin,
    generics.ListAPIView
):
    pagination_class = TransactionPagination

    def get_queryset(self):
        params = self.request.query_params
        logger.info(
            "Transaction history requested from=%s to=%s",
            params.get("from", "-"), params.get("to", "-"),
        )
        filters = TransactionFiltersSerializer(data={
            field: params[param]
            for param, field in [("from", "from_date"), ("to", "to_date")]
            if param in params
        })
        filters.is_valid(raise_exception=True)
        dates = filters.validated_data
        queryset = super().get_queryset()
        if "from_date" in dates:
            queryset = queryset.filter(created_at__date__gte=dates["from_date"])
        if "to_date" in dates:
            queryset = queryset.filter(created_at__date__lte=dates["to_date"])
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        logger.info(
            "Transaction history returned total=%s on_page=%s",
            response.data["count"], len(response.data["results"]),
        )
        return response



class ReadTransactionApiView(
    UserTransactionsMixin,
    generics.RetrieveAPIView
):
    def get_object(self):
        logger.info("Transaction requested entry_id=%s", self.kwargs["pk"])
        entry = super().get_object()
        logger.info(
            "Transaction returned entry_id=%s category=%s amount=%s",
            entry.pk, entry.category, entry.amount,
        )
        return entry
