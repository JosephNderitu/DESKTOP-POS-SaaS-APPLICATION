from django.contrib.admin.models import LogEntry
from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import get_tenant_model, schema_context


class Command(BaseCommand):
    help = "Create missing tenant django_admin_log tables for tenant admin saves."

    def handle(self, *args, **options):
        TenantModel = get_tenant_model()
        repaired = 0
        skipped = 0

        for tenant in TenantModel.objects.exclude(schema_name="public"):
            with schema_context(tenant.schema_name):
                existing_tables = connection.introspection.table_names()

                if LogEntry._meta.db_table in existing_tables:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"{tenant.schema_name}: django_admin_log already exists"
                        )
                    )
                    continue

                with connection.schema_editor() as schema_editor:
                    schema_editor.create_model(LogEntry)

                repaired += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{tenant.schema_name}: created django_admin_log"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Repair complete. Created {repaired}; skipped {skipped}."
            )
        )
