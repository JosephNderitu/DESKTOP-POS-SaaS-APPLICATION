# core_backend/models_base.py
import uuid
from django.db import models

class AbstractBaseUUIDModel(models.Model):
    """
    Abstract base class that replaces standard integer IDs with UUIDs
    and provides automatic timestamping for auditing and database syncing.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_synced = models.BooleanField(default=True)  # Crucial flag for the PyQt offline sync agent

    class Meta:
        abstract = True