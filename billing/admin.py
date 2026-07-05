from django.contrib import admin
from django.utils.html import format_html
from .models import SubscriptionPlan, Transaction


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'billing_cycle', 'price_kes', 'price_usd', 'max_terminals', 'max_staff', 'is_active')
    list_filter = ('billing_cycle', 'is_active')
    prepopulated_fields = {'code': ('name',)}


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant_schema', 'plan', 'gateway', 'amount_display', 'status_badge', 'created_at')
    list_filter = ('gateway', 'status', 'plan')
    search_fields = ('tenant_schema', 'gateway_reference')
    readonly_fields = ('raw_payload',)

    def amount_display(self, obj):
        return f"{obj.currency} {obj.amount:,.2f}"
    amount_display.short_description = "Amount"

    def status_badge(self, obj):
        colors = {'PENDING': '#F59E0B', 'SUCCESS': '#008C72', 'FAILED': '#DC2626', 'CANCELLED': '#64748B'}
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; border-radius:10px; font-size:11px; font-weight:700;">{}</span>',
            colors.get(obj.status, '#64748B'), obj.status
        )
    status_badge.short_description = "Status"