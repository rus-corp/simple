from django.core.management.base import BaseCommand

from accounts.models import AccountORM
from clients.errors import EmailAlreadyExists
from clients.services import RegistrationClientService


DEMO_EMAILS = [
    "ivan@example.com",
    "anton@example.com",
    "valera@example.com",
    "petr@example.com",
]
DEMO_PASSWORD = "Str0ng-Passw0rd!"


class Command(BaseCommand):
    help = "Create demo clients, each with an account and the welcome bonus."

    def handle(self, *args, **options):
        for email in DEMO_EMAILS:
            try:
                RegistrationClientService().execute(
                    email=email,
                    password=DEMO_PASSWORD,
                )
                status = self.style.SUCCESS("created")
            except EmailAlreadyExists:
                status = self.style.WARNING("exists ")

            account = AccountORM.objects.get(client__user__email=email)
            self.stdout.write(
                f"{status} {email:<20} account={account.account_number} "
                f"balance={account.balance}"
            )

        self.stdout.write(f"Password for all demo clients: {DEMO_PASSWORD}")
