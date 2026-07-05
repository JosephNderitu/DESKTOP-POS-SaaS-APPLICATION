from datetime import timedelta
from django.utils import timezone


def activate_subscription(transaction):
    """Called by every gateway's success path. Idempotent-ish: only acts on
    a PENDING transaction, so a retried webhook can't double-activate."""
    from tenants.models import Client, log_platform_action

    tenant = Client.objects.filter(schema_name=transaction.tenant_schema).first()
    if not tenant:
        return

    days = 365 if transaction.plan.billing_cycle == 'YEARLY' else 30
    tenant.subscription_status = 'ACTIVE'
    tenant.subscription_plan = transaction.plan.code
    tenant.paid_until = timezone.now().date() + timedelta(days=days)
    tenant.on_trial = False
    tenant.save()

    log_platform_action(
        'system', f'SUBSCRIPTION_ACTIVATED:{transaction.gateway}',
        tenant.schema_name, f"Plan: {transaction.plan.code}, Txn #{transaction.id}"
    )

    transaction.status = 'SUCCESS'
    transaction.save(update_fields=['status'])