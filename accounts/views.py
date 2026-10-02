from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from .models import AccountORM
from .serializer import AccountSerializer


class ReadAccountApiView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSerializer

    def get_object(self):
        account = get_object_or_404(AccountORM, client__user=self.request.user)
        self.check_object_permissions(self.request, account)
        return account