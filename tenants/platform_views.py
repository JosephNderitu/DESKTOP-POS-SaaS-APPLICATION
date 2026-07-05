from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Client, Domain, log_platform_action
from .permissions import IsPlatformOwner
from .serializers import ClientAdminSerializer


def _get_tenant_or_404(schema_name):
    return Client.objects.filter(schema_name=schema_name).first()


class TenantListView(APIView):
    """GET /api/v1/platform/stores/ — every store on the platform, one call."""
    permission_classes = [IsAuthenticated, IsPlatformOwner]

    def get(self, request):
        tenants = Client.objects.exclude(schema_name='public').order_by('name')
        return Response(ClientAdminSerializer(tenants, many=True).data)


class TenantSuspendView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOwner]

    def post(self, request, schema_name):
        tenant = _get_tenant_or_404(schema_name)
        if not tenant:
            return Response({"detail": "Store not found."}, status=status.HTTP_404_NOT_FOUND)
        tenant.subscription_status = 'SUSPENDED'
        tenant.suspended_reason = request.data.get('reason', '')
        tenant.save()
        log_platform_action(request.user, 'SUSPEND', tenant.schema_name, request.data.get('reason', ''))
        return Response({"detail": f"{tenant.name} suspended.", "status": tenant.subscription_status})


class TenantReactivateView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOwner]

    def post(self, request, schema_name):
        tenant = _get_tenant_or_404(schema_name)
        if not tenant:
            return Response({"detail": "Store not found."}, status=status.HTTP_404_NOT_FOUND)
        tenant.subscription_status = 'ACTIVE'
        tenant.suspended_reason = ''
        tenant.save()
        log_platform_action(request.user, 'REACTIVATE', tenant.schema_name)
        return Response({"detail": f"{tenant.name} reactivated.", "status": tenant.subscription_status})


class TenantTerminateView(APIView):
    """
    Marks the subscription as terminated. Deliberately does NOT drop the
    tenant's schema — that's a separate, manual, destructive action (see note below).
    """
    permission_classes = [IsAuthenticated, IsPlatformOwner]

    def post(self, request, schema_name):
        tenant = _get_tenant_or_404(schema_name)
        if not tenant:
            return Response({"detail": "Store not found."}, status=status.HTTP_404_NOT_FOUND)
        tenant.subscription_status = 'TERMINATED'
        tenant.save()
        log_platform_action(request.user, 'TERMINATE', tenant.schema_name)
        return Response({"detail": f"{tenant.name} terminated.", "status": tenant.subscription_status})


class TenantRenameDomainView(APIView):
    """POST body: {"new_domain": "newname.localhost"}"""
    permission_classes = [IsAuthenticated, IsPlatformOwner]

    def post(self, request, schema_name):
        tenant = _get_tenant_or_404(schema_name)
        if not tenant:
            return Response({"detail": "Store not found."}, status=status.HTTP_404_NOT_FOUND)
        new_domain = request.data.get('new_domain')
        if not new_domain:
            return Response({"detail": "new_domain is required."}, status=status.HTTP_400_BAD_REQUEST)
        domain_obj = Domain.objects.filter(tenant=tenant, is_primary=True).first()
        if not domain_obj:
            return Response({"detail": "No primary domain found."}, status=status.HTTP_404_NOT_FOUND)
        domain_obj.domain = new_domain
        domain_obj.save()
        log_platform_action(request.user, 'RENAME_DOMAIN', tenant.schema_name, f"New domain: {new_domain}")
        return Response({"detail": f"Domain updated to {new_domain}."})


class TenantUserListView(APIView):
    """
    GET /api/v1/platform/stores/<schema_name>/users/
    This is the one place actual cross-schema visibility happens —
    schema_context() temporarily points the DB connection at the tenant's
    schema so User.objects queries that store's staff table, then restores
    the connection to public automatically on exit.
    """
    permission_classes = [IsAuthenticated, IsPlatformOwner]

    def get(self, request, schema_name):
        tenant = _get_tenant_or_404(schema_name)
        if not tenant:
            return Response({"detail": "Store not found."}, status=status.HTTP_404_NOT_FOUND)
        with schema_context(tenant.schema_name):
            from users.models import User
            users_qs = User.objects.all().values('id', 'username', 'email', 'role', 'is_active', 'date_joined')
            return Response(list(users_qs))


class TenantUserSuspendView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOwner]

    def post(self, request, schema_name, user_id):
        tenant = _get_tenant_or_404(schema_name)
        if not tenant:
            return Response({"detail": "Store not found."}, status=status.HTTP_404_NOT_FOUND)
        with schema_context(tenant.schema_name):
            from users.models import User
            store_user = User.objects.filter(id=user_id).first()
            if not store_user:
                return Response({"detail": "User not found in this store."}, status=status.HTTP_404_NOT_FOUND)
            store_user.is_active = False
            store_user.save()
            log_platform_action(request.user, 'SUSPEND_STORE_USER', tenant.schema_name, f"User: {store_user.username}")
            return Response({"detail": f"{store_user.username} suspended in {tenant.name}."})