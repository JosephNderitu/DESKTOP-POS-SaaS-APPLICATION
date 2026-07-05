from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tenants'

    def ready(self):
        from django.contrib import admin

        def _platform_owner_only(self, request):
            return bool(request.user and request.user.is_active and request.user.is_superuser)

        admin.site.has_permission = _platform_owner_only.__get__(admin.site, admin.site.__class__)

        def _platform_index(self, request, extra_context=None):
            from .models import Client, PlatformAuditLog

            extra_context = extra_context or {}
            extra_context.update({
                "total_stores": Client.objects.exclude(schema_name='public').count(),
                "active_stores": Client.objects.filter(subscription_status='ACTIVE').count(),
                "trial_stores": Client.objects.filter(subscription_status='TRIAL').count(),
                "suspended_stores": Client.objects.filter(subscription_status='SUSPENDED').count(),
                "terminated_stores": Client.objects.filter(subscription_status='TERMINATED').count(),
                "recent_logs": PlatformAuditLog.objects.all()[:5],
            })
            return admin.AdminSite.index(self, request, extra_context)

        admin.site.index = _platform_index.__get__(admin.site, admin.site.__class__)
        admin.site.index_template = "admin/platform_dashboard.html"