from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from tenants.models import LoginEvent


class Command(BaseCommand):
    help = (
        "Deletes LoginEvent rows older than a given number of days (default 365). "
        "This command only performs the cleanup — it does not schedule itself. "
        "Run it periodically via cron, Windows Task Scheduler, or Celery beat."
    )

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=365, help='Delete login events older than this many days.')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting anything.')

    def handle(self, *args, **options):
        # LoginEvent lives only in the public schema — wrapped explicitly
        # rather than assuming the default DB connection is already there,
        # since management commands don't always run with that guarantee.
        with schema_context(get_public_schema_name()):
            cutoff = timezone.now() - timedelta(days=options['days'])
            queryset = LoginEvent.objects.filter(timestamp__lt=cutoff)
            count = queryset.count()

            if options['dry_run']:
                self.stdout.write(self.style.WARNING(
                    f"[DRY RUN] Would delete {count} login event(s) older than {options['days']} days."
                ))
                return

            queryset.delete()
            self.stdout.write(self.style.SUCCESS(
                f"Deleted {count} login event(s) older than {options['days']} days."
            ))