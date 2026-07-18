from django.db import connection
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_tenants.utils import get_public_schema_name, schema_context

from .models import User


def _sync_cashier_count():
    """
    Recomputes this schema's active cashier count and writes it to the
    matching Client row in the public schema. Runs on every relevant User
    save/delete, so platform_store_activity_api can just read
    Client.cashier_count directly instead of entering every tenant's schema
    on every dashboard page load.
    """
    schema_name = connection.schema_name
    if schema_name == get_public_schema_name():
        return  # a public-schema User save (e.g. platform superuser) — not a store's cashier count

    count = User.objects.filter(role='CASHIER', is_active=True).count()

    with schema_context(get_public_schema_name()):
        from tenants.models import Client
        Client.objects.filter(schema_name=schema_name).update(cashier_count=count)


@receiver(post_save, sender=User)
def on_user_saved(sender, instance, **kwargs):
    _sync_cashier_count()


@receiver(post_delete, sender=User)
def on_user_deleted(sender, instance, **kwargs):
    _sync_cashier_count()