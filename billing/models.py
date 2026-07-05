from django.db import models


class SubscriptionPlan(models.Model):
    BILLING_CYCLE_CHOICES = [('MONTHLY', 'Monthly'), ('YEARLY', 'Yearly')]

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    tagline = models.CharField(max_length=200, blank=True)
    price_kes = models.DecimalField(max_digits=10, decimal_places=2)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES, default='MONTHLY')
    max_terminals = models.PositiveIntegerField(default=1)
    max_staff = models.PositiveIntegerField(default=3)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return self.name


class Transaction(models.Model):
    GATEWAY_CHOICES = [('STRIPE', 'Stripe'), ('PAYPAL', 'PayPal'), ('MPESA', 'M-Pesa')]
    STATUS_CHOICES = [('PENDING', 'Pending'), ('SUCCESS', 'Success'), ('FAILED', 'Failed'), ('CANCELLED', 'Cancelled')]

    # Stored as a plain string rather than a FK — Client lives in the same
    # shared schema so a FK would technically work, but keeping this as a
    # string keeps Transaction fully decoupled from tenant lifecycle changes.
    tenant_schema = models.CharField(max_length=100)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    gateway = models.CharField(max_length=10, choices=GATEWAY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    gateway_reference = models.CharField(max_length=255, blank=True)
    raw_payload = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tenant_schema} · {self.gateway} · {self.status}"