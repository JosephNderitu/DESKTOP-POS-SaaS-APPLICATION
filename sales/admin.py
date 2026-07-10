from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from tenants.admin_site import tenant_admin_site
from .models import Payment, Sale, SaleItem

STATUS_COLORS = {
    'COMPLETED': '#008C72',
    'PENDING': '#F59E0B',
    'CANCELLED': '#DC2626',
}

PAYMENT_COLORS = {
    'CASH': '#059669',
    'MPESA': '#00A651',
    'STRIPE': '#635BFF',
    'PAYPAL': '#0070BA',
}

PAYMENT_LABELS = {
    'CASH': 'Cash',
    'MPESA': 'M-Pesa',
    'STRIPE': 'Stripe',
    'PAYPAL': 'PayPal',
}


def _badge(text, color):
    return format_html(
        '<span style="background:{}; color:#fff; padding:3px 10px; '
        'border-radius:10px; font-size:11px; font-weight:700; white-space:nowrap;">{}</span>',
        color, text
    )


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    fields = ('product', 'quantity', 'unit_price', 'total_price')
    readonly_fields = ('total_price',)
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False  # sale items come from checkout, not hand-editing


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ('method', 'amount', 'transaction_reference', 'gateway_response')
    readonly_fields = ('transaction_reference', 'gateway_response')

    def has_add_permission(self, request, obj=None):
        return False


class SaleAdmin(admin.ModelAdmin):
    list_display = (
        'short_id', 'cashier_username', 'payment_method_badge',
        'total_amount', 'discount_amount', 'status_badge', 'created_at',
    )
    list_filter = ('status', 'cashier', 'payments__method')
    search_fields = ('id', 'cashier__username', 'payments__transaction_reference')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_per_page = 25
    inlines = [SaleItemInline, PaymentInline]
    readonly_fields = ('subtotal', 'discount_amount', 'tax_amount', 'total_amount', 'created_at')

    def get_queryset(self, request):
        # payments__method in list_filter traverses a reverse relation —
        # distinct() prevents a sale from appearing twice if it ever ends
        # up with more than one Payment row (e.g. a retried attempt).
        return super().get_queryset(request).select_related('cashier').prefetch_related('payments').distinct()

    def short_id(self, obj):
        return f"#{str(obj.id)[:8]}"
    short_id.short_description = "Sale"

    def cashier_username(self, obj):
        return obj.cashier.username
    cashier_username.short_description = "Cashier"
    cashier_username.admin_order_field = 'cashier__username'

    def payment_method_badge(self, obj):
        methods = {p.method for p in obj.payments.all()}
        if not methods:
            return "—"
        badges = [_badge(PAYMENT_LABELS.get(m, m.title()), PAYMENT_COLORS.get(m, '#64748B')) for m in methods]
        return mark_safe(" ".join(badges))
    payment_method_badge.short_description = "Payment Method"

    def status_badge(self, obj):
        return _badge(obj.get_status_display(), STATUS_COLORS.get(obj.status, '#64748B'))
    status_badge.short_description = "Status"


tenant_admin_site.register(Sale, SaleAdmin)