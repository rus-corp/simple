from django.db import models
from common.models import UUIDModel


class ClientsORM(UUIDModel):
    user = models.OneToOneField(
        to="users.User",
        on_delete=models.PROTECT
    )