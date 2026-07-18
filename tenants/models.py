from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.utils import timezone
from datetime import timedelta

class Client(TenantMixin):
    """
    Represents an individual company/business registering on your SaaS platform.
    """
    name = models.CharField(max_length=100)
    paid_until = models.DateField(help_text="Tracks subscription lifecycle")
    on_trial = models.BooleanField(default=True)
    created_on = models.DateField(auto_now_add=True)
    owner_email = models.EmailField(blank=True, default='')
    # Cached counters/state — avoids per-page-load cross-schema queries.
    # Kept in sync by signals (cashier_count) and by the analytics endpoint
    # itself (last_known_engagement) rather than recomputed live every time.
    cashier_count = models.PositiveIntegerField(default=0)
    last_known_engagement = models.CharField(max_length=20, blank=True, default='')

    # Automatically clean up database schemas if a tenant account is dropped
    auto_create_schema = True
    # --- Platform-owner governance fields ---
    SUBSCRIPTION_STATUS_CHOICES = [
        ('TRIAL', 'Trial'),
        ('PENDING_PAYMENT', 'Pending Payment'),
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
        ('TERMINATED', 'Terminated'),
    ]
    subscription_status = models.CharField(
        max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default='TRIAL'
    )
    subscription_plan = models.CharField(max_length=50, default='basic')
    suspended_reason = models.TextField(blank=True, default='')
    
    # ... existing fields ...
    trial_start_date = models.DateTimeField(null=True, blank=True)
    trial_period_days = models.PositiveIntegerField(default=14)

    def save(self, *args, **kwargs):
        if self.pk is None and self.trial_start_date is None:
            self.trial_start_date = timezone.now()
        super().save(*args, **kwargs)

    @property
    def trial_end_date(self):
        if not self.trial_start_date:
            return None
        return self.trial_start_date + timedelta(days=self.trial_period_days)

    @property
    def days_left_in_trial(self):
        if self.subscription_status != 'TRIAL' or not self.trial_end_date:
            return None
        return max((self.trial_end_date - timezone.now()).days, 0)

    @property
    def is_trial_expired(self):
        return self.subscription_status == 'TRIAL' and self.trial_end_date and timezone.now() > self.trial_end_date

    def __str__(self):
        return self.name

class PlatformAuditLog(models.Model):
    """One row per platform-owner action. Append-only, never edited or deleted."""
    actor_username = models.CharField(max_length=150)
    action = models.CharField(max_length=100)
    target_tenant = models.CharField(max_length=100)
    reason = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} · {self.actor_username} · {self.action} · {self.target_tenant}"


def log_platform_action(actor, action, target_tenant, reason=''):
    """Call this one line from any platform view that changes tenant state."""
    PlatformAuditLog.objects.create(
        actor_username=getattr(actor, 'username', 'system'),
        action=action,
        target_tenant=target_tenant,
        reason=reason,
    )
 
class LoginEvent(models.Model):
    """
    One row per successful store-user login, written to the PUBLIC schema
    regardless of which tenant the login happened against. This is what
    lets the platform dashboard chart login activity and flag inactive
    stores with a single query, instead of looping schema_context() across
    every tenant's own database just to answer "who logged in recently".
    """
    tenant_schema = models.CharField(max_length=100)
    tenant_name = models.CharField(max_length=100, blank=True, default='')
    username = models.CharField(max_length=150)
    role = models.CharField(max_length=20, blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant_schema', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} · {self.tenant_schema} · {self.username}"


def log_login_event(tenant, user):
    """Call this from POSLoginView on every successful login."""
    from django_tenants.utils import get_public_schema_name, schema_context
    with schema_context(get_public_schema_name()):
        LoginEvent.objects.create(
            tenant_schema=tenant.schema_name,
            tenant_name=tenant.name,
            username=user.username,
            role=getattr(user, 'role', ''),
        )
           
class Domain(DomainMixin):
    """
    Maps an sub-domain routing token to a specific client schema 
    (e.g., 'nairobibranch.smartpos.com' -> routes queries to client DB space).
    """
    pass

