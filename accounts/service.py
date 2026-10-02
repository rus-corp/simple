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


def generate_account_number() -> str:
    return f"{secrets.randbelow(10**10):010d}"




class AccountService:
    def create(
        self,
        *,
        client: ClientsORM
    ) -> AccountORM:
        for _ in range(MAX_ACCOUNT_NUMBER_ATTEMPTS):
            account_number = generate_account_number()
            try:
                with transaction.atomic():
                    account = AccountORM.objects.create(
                        client=client,
                        account_number=account_number
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
                    continue
                raise
        raise AccountNumberGenerationError(
            "Could not generate a unique account number"
        )
