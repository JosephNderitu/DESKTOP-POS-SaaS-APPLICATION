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

    # Automatically clean up database schemas if a tenant account is dropped
    auto_create_schema = True
    # --- Platform-owner governance fields ---
    SUBSCRIPTION_STATUS_CHOICES = [
        ('TRIAL', 'Trial'),
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
    
class Domain(DomainMixin):
    """
    Maps an sub-domain routing token to a specific client schema 
    (e.g., 'nairobibranch.smartpos.com' -> routes queries to client DB space).
    """
    pass