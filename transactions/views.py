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





class CreateTransferApiView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

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



class ReadTransactionApiView(
    UserTransactionsMixin,
    generics.RetrieveAPIView
):
    pass