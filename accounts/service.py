import logging
import secrets

from django.db import IntegrityError, transaction
from psycopg.errors import UniqueViolation

from accounts.errors import AccountNumberGenerationError
from accounts.models import AccountORM
from clients.models import ClientsORM


ACCOUNT_NUMBER_UNIQUE_CONSTRAINT = (
    "accounts_accountorm_account_number_key"
)
MAX_ACCOUNT_NUMBER_ATTEMPTS = 5

logger = logging.getLogger(__name__)


def generate_account_number() -> str:
    return f"{secrets.randbelow(10**10):010d}"




class AccountService:
    "This class create accounts after registration"
    def create(
        self,
        *,
        client: ClientsORM
    ) -> AccountORM:
        logger.info("Account creation started client_id=%s", client.pk)
        for attempt in range(1, MAX_ACCOUNT_NUMBER_ATTEMPTS + 1):
            account_number = generate_account_number()
            try:
                with transaction.atomic():
                    account = AccountORM.objects.create(
                        client=client,
                        account_number=account_number
                    )
                logger.info(
                    "Account created account_id=%s account_number=%s client_id=%s attempt=%s",
                    account.pk, account.account_number, client.pk, attempt,
                )
                return account
            except IntegrityError as error:
                cause = error.__cause__
                if (
                    isinstance(cause, UniqueViolation)
                    and cause.diag.table_name == AccountORM._meta.db_table
                    and cause.diag.constraint_name
                    == ACCOUNT_NUMBER_UNIQUE_CONSTRAINT
                ):
                    logger.warning(
                        "Account number collision, generating another one client_id=%s attempt=%s",
                        client.pk, attempt,
                    )
                    continue
                logger.exception(
                    "Account creation failed client_id=%s", client.pk,
                )
                raise
        logger.error(
            "Account creation failed: no unique account number after %s attempts client_id=%s",
            MAX_ACCOUNT_NUMBER_ATTEMPTS, client.pk,
        )
        raise AccountNumberGenerationError(
            "Could not generate a unique account number"
        )
