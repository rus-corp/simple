from django.db import models
from common.models import UUIDModel


class ClientsORM(UUIDModel):
    "One to one relation to User. This model has balance, account and transactions"
    user = models.OneToOneField(
        to="users.User",
        on_delete=models.PROTECT
    )