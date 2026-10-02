from django.urls import path
from .views import CreateTransferApiView, ReadTransactionApiView, ReadTransactionsApiView

app_name = 'transactions'


urlpatterns = [
    path("transfers/", CreateTransferApiView.as_view(), name="transfer-create"),
    path("transactions/", ReadTransactionsApiView.as_view(), name="transaction-list"),
    path("transactions/<uuid:pk>/", ReadTransactionApiView.as_view(), name="transaction-detail"),
]
