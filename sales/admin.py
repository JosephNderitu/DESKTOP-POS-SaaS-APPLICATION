from django.contrib import admin
from tenants.admin_site import tenant_admin_site
from .models import Sale, SaleItem, Payment


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'cashier', 'total_amount', 'status', 'created_at')
    list_filter = ('status',)
    inlines = [SaleItemInline, PaymentInline]


tenant_admin_site.register(Sale, SaleAdmin)