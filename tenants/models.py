from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

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

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    """
    Maps an sub-domain routing token to a specific client schema 
    (e.g., 'nairobibranch.smartpos.com' -> routes queries to client DB space).
    """
    pass