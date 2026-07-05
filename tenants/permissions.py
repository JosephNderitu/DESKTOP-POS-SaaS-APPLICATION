from django.db import connection
from django_tenants.utils import get_public_schema_name
from rest_framework.permissions import BasePermission


class IsPlatformOwner(BasePermission):
    """
    True only for a superuser authenticated while the active connection
    is on the public schema. Store-level superusers live inside their own
    tenant schema and structurally can't reach these endpoints at all —
    this check is defense in depth on top of that isolation, not the only line of defense.
    """
    message = "Platform owner access required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
            and connection.schema_name == get_public_schema_name()
        )