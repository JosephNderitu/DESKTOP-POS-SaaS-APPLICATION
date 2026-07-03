from django.contrib import admin
from .models import Sale, SaleItem, Payment

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'cashier', 'total_amount', 'status', 'created_at')
    list_filter = ('status',)
    inlines = [SaleItemInline, PaymentInline]