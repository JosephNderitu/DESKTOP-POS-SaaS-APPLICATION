from django.contrib.admin import AdminSite
from django.db.models import F


class TenantAdminSite(AdminSite):
    site_header = "Store Admin"
    site_title = "Store Admin"
    index_title = "Store Management"
    index_template = "admin/tenant_dashboard.html"

    def index(self, request, extra_context=None):
        from inventory.models import Product, Category
        from django.contrib.auth import get_user_model

        User = get_user_model()
        extra_context = extra_context or {}
        extra_context.update({
            "total_products": Product.objects.count(),
            "active_products": Product.objects.filter(is_active=True).count(),
            "low_stock_count": Product.objects.filter(stock_quantity__lte=F('low_stock_threshold')).count(),
            "total_categories": Category.objects.count(),
            "total_staff": User.objects.filter(is_active=True).count(),
        })
        return super().index(request, extra_context)


tenant_admin_site = TenantAdminSite(name='tenant_admin')