from django.core.management.base import BaseCommand
from django_tenants.utils import get_public_schema_name, schema_context

from tenants.models import Client


class Command(BaseCommand):
    help = (
        "One-time backfill for Client.cashier_count on existing stores. "
        "After this runs once, users.signals keeps the count in sync automatically — "
        "this command only needs to be re-run if the counter ever drifts out of sync."
    )

    def handle(self, *args, **options):
        tenants = Client.objects.exclude(schema_name=get_public_schema_name())
        updated = 0

        for tenant in tenants:
            with schema_context(tenant.schema_name):
                from users.models import User
                count = User.objects.filter(role='CASHIER', is_active=True).count()
            tenant.cashier_count = count
            tenant.save(update_fields=['cashier_count'])
            updated += 1
            self.stdout.write(f"  {tenant.schema_name}: {count} cashiers")

        self.stdout.write(self.style.SUCCESS(f"Backfilled cashier_count for {updated} store(s)."))