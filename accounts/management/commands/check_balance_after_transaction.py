import json
from time import perf_counter

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError
from django.utils import timezone

from accounts.check_balance import check_balance_after_transaction


class Command(BaseCommand):
    help = "Compare account balances with signed ledger sums without changing any data."

    def handle(self, *args, **options):
        started_at = timezone.now()
        started = perf_counter()
        try:
            mismatches = check_balance_after_transaction()
        except DatabaseError as error:
            raise CommandError("Balance check failed: database query could not complete.") from error

        self.stdout.write(json.dumps({
            "event": "balance_check",
            "started_at": started_at.isoformat(),
            "duration_ms": round((perf_counter() - started) * 1000, 2),
            "status": "mismatch" if mismatches else "ok",
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        }, default=str))

        if mismatches:
            raise CommandError(f"Balance mismatch found for {len(mismatches)} account(s).")
