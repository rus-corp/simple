import logging

from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from psycopg.errors import UniqueViolation

from clients.models import ClientsORM
from common.logging import mask_email
from .errors import EmailAlreadyExists
from accounts.service import AccountService
from transactions.service import WelcomeBonusService




User = get_user_model()
EMAIL_UNIQUE_CONSTRAINT = "users_user_email_key"

logger = logging.getLogger(__name__)



class RegistrationClientService:
    def execute(
        self,
        *,
        email: str,
        password: str
    ):
        logger.info("Registration started email=%s", mask_email(email))
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=password
                )

                client = ClientsORM.objects.create(user=user)

                account = AccountService().create(
                    client=client
                )
                WelcomeBonusService().grant(
                    account_id=account.pk
                )

        except IntegrityError as error:
            cause = error.__cause__

            if (
                isinstance(cause, UniqueViolation)
                and cause.diag.table_name == User._meta.db_table
                and cause.diag.constraint_name == EMAIL_UNIQUE_CONSTRAINT
            ):
                logger.warning(
                    "Registration rejected: email already exists, nothing was created email=%s",
                    mask_email(email),
                )
                raise EmailAlreadyExists() from error
            logger.exception(
                "Registration failed and was rolled back email=%s",
                mask_email(email),
            )
            raise

        logger.info(
            "Registration completed user_id=%s client_id=%s account_id=%s",
            user.pk, client.pk, account.pk,
        )
        return user
