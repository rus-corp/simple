from rest_framework.permissions import IsAuthenticated
from .serializers import TransactionHistorySerializer
from .models import LedgerEntriesORM

class UserTransactionsMixin:
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionHistorySerializer

    def get_queryset(self):
        return (
            LedgerEntriesORM.objects
            .filter(account__client__user=self.request.user)
            .order_by("-created_at", "-pk")
        )