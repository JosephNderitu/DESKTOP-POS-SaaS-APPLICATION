from django.contrib import admin
from django.utils.html import format_html

from tenants.admin_site import tenant_admin_site
from .models import Category, Product


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "Products"


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'formatted_price', 'stock_badge', 'is_active')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'sku')
    list_per_page = 25
    readonly_fields = ('image_processed',)

    def formatted_price(self, obj):
        return f"KES {obj.selling_price:,.2f}"
    formatted_price.short_description = "Price"

    def stock_badge(self, obj):
        if obj.stock_quantity <= 0:
            color, label = '#DC2626', 'Out of stock'
        elif obj.stock_quantity <= obj.low_stock_threshold:
            color, label = '#F59E0B', f'Low ({obj.stock_quantity})'
        else:
            color, label = '#008C72', f'{obj.stock_quantity} in stock'
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; '
            'border-radius:8px; font-size:11px; font-weight:700;">{}</span>',
            color, label
        )
    stock_badge.short_description = "Stock"


tenant_admin_site.register(Category, CategoryAdmin)
tenant_admin_site.register(Product, ProductAdmin)