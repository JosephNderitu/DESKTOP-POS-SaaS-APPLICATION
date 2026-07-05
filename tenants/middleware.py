from django.http import JsonResponse
from django_tenants.utils import get_public_schema_name


class TenantAccessControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, 'tenant', None)
        if tenant and tenant.schema_name != get_public_schema_name():

            # Trial ran out on its own — flip status automatically, no manual step needed
            if tenant.is_trial_expired:
                tenant.subscription_status = 'SUSPENDED'
                tenant.suspended_reason = 'Trial period ended.'
                tenant.save()

            if tenant.subscription_status in ('SUSPENDED', 'TERMINATED'):
                return JsonResponse(
                    {"detail": self._message_for(tenant), "subscription_status": tenant.subscription_status},
                    status=402,
                )
        return self.get_response(request)

    def _message_for(self, tenant):
        if tenant.subscription_status == 'TERMINATED':
            return "This store's subscription has been terminated. Please contact support to reactivate your account."
        if tenant.suspended_reason == 'Trial period ended.':
            return "Your free trial has ended. Subscribe to a plan to continue using this store."
        return "This store's access has been suspended. Please contact support."