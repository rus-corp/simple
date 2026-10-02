from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from psycopg.errors import UniqueViolation

from clients.models import ClientsORM
from .errors import EmailAlreadyExists



User = get_user_model()
EMAIL_UNIQUE_CONSTRAINT = "users_user_email_key"



class RegistrationClientService:
    def execute(
        self,
        *,
        email: str,
        password: str
    ):
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=password
                )

                client = ClientsORM.objects.create(user=user)


        except IntegrityError as error:
            cause = error.__cause__

            if (
                isinstance(cause, UniqueViolation)
                and cause.diag.table_name == User._meta.db_table
                and cause.diag.constraint_name == EMAIL_UNIQUE_CONSTRAINT
            ):
                raise EmailAlreadyExists() from error
            raise

        return user
