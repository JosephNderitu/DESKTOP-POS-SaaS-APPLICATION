from django.contrib import admin
from django.utils.html import format_html

from .models import Client, Domain, PlatformAuditLog, log_platform_action


@admin.action(description="Suspend selected stores")
def suspend_stores(modeladmin, request, queryset):
    for tenant in queryset:
        tenant.subscription_status = 'SUSPENDED'
        tenant.save()
        log_platform_action(request.user, 'SUSPEND', tenant.schema_name, 'Bulk action via admin')


@admin.action(description="Reactivate selected stores")
def reactivate_stores(modeladmin, request, queryset):
    for tenant in queryset:
        tenant.subscription_status = 'ACTIVE'
        tenant.save()
        log_platform_action(request.user, 'REACTIVATE', tenant.schema_name, 'Bulk action via admin')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'schema_name', 'status_badge', 'subscription_plan', 'trial_countdown', 'created_on')
    list_filter = ('subscription_status', 'subscription_plan')
    search_fields = ('name', 'schema_name')
    actions = [suspend_stores, reactivate_stores]
    readonly_fields = ('created_on',)

    def status_badge(self, obj):
        colors = {'TRIAL': '#F59E0B', 'ACTIVE': '#008C72', 'SUSPENDED': '#DC2626', 'TERMINATED': '#7F1D1D'}
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:10px; font-size:11px; font-weight:700;">{}</span>',
            colors.get(obj.subscription_status, '#64748B'), obj.get_subscription_status_display()
        )
    status_badge.short_description = "Status"

    def trial_countdown(self, obj):
        if obj.subscription_status != 'TRIAL':
            return "—"
        days = obj.days_left_in_trial
        return f"{days} day{'s' if days != 1 else ''} left" if days is not None else "—"
    trial_countdown.short_description = "Trial"

    def save_model(self, request, obj, form, change):
        """Catches admin-form edits (not just API calls) so nothing slips past the audit log."""
        previous_status = None
        if change:
            previous_status = Client.objects.filter(pk=obj.pk).values_list('subscription_status', flat=True).first()

        super().save_model(request, obj, form, change)

        if change and previous_status and previous_status != obj.subscription_status:
            log_platform_action(
                request.user, f"STATUS_CHANGE:{previous_status}->{obj.subscription_status}",
                obj.schema_name, "Changed via Django admin"
            )
        elif not change:
            log_platform_action(request.user, 'CREATE', obj.schema_name, "Store created via Django admin")


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')
    list_filter = ('is_primary',)
    search_fields = ('domain',)


@admin.register(PlatformAuditLog)
class PlatformAuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor_username', 'action', 'target_tenant', 'reason')
    list_filter = ('action',)
    search_fields = ('actor_username', 'target_tenant')
    ordering = ('-timestamp',)
    readonly_fields = ('actor_username', 'action', 'target_tenant', 'reason', 'timestamp')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False