from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import POSLoginView
from inventory.views import TenantProductViewSet
from tenants.admin_site import tenant_admin_site

tenant_router = DefaultRouter()
tenant_router.register(r'products', TenantProductViewSet, basename='tenant-products')

from django.conf import settings
from django.conf.urls.static import static

#billing views
from billing.views import InitiateSubscriptionCheckoutView
#password reset views
from users.views import POSLoginView, PasswordResetRequestView, PasswordResetConfirmView, password_reset_confirm_page
from sales.views import (
    SalesCheckoutView, SaleStatusView, SaleStripeConfirmView,
    SaleMpesaCallbackView, SaleMarkCancelledView, sale_payment_success_page, sale_payment_cancel_page,
)
from sales.analytics import sales_analytics_api, cashier_performance_api

urlpatterns = [
    path('admin/', tenant_admin_site.urls),  # scoped site — no Client/Domain/audit models exist here
    path('api/v1/login/', POSLoginView.as_view(), name='pos_login'),
    path('api/v1/inventory/', include(tenant_router.urls)),
    path('api/v1/billing/checkout/', InitiateSubscriptionCheckoutView.as_view(), name='billing_checkout'),
    
    #password reset views
    path('api/v1/login/', POSLoginView.as_view(), name='pos_login'),
    path('api/v1/password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('api/v1/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/confirm/', password_reset_confirm_page, name='password_reset_confirm_page'),
    path('api/v1/inventory/', include(tenant_router.urls)),
    
    #sales views
    path('api/v1/sales/checkout/', SalesCheckoutView.as_view(), name='sales_checkout'),
    path('api/v1/sales/<uuid:sale_id>/status/', SaleStatusView.as_view(), name='sales_status'),
    path('api/v1/sales/<uuid:sale_id>/confirm-stripe/', SaleStripeConfirmView.as_view(), name='sales_confirm_stripe'),
    path('api/v1/sales/webhooks/mpesa/', SaleMpesaCallbackView.as_view(), name='sales_mpesa_webhook'),
    path('sales/payment/success/', sale_payment_success_page, name='sale_payment_success_page'),
    path('sales/payment/cancel/', sale_payment_cancel_page, name='sale_payment_cancel_page'),
    path('api/v1/sales/<uuid:sale_id>/cancel/', SaleMarkCancelledView.as_view(), name='sales_mark_cancelled'),
    #analytics view
    path('api/v1/sales/analytics/', sales_analytics_api, name='sales_analytics_api'),
    path('api/v1/sales/cashier-performance/', cashier_performance_api, name='sales_cashier_performance'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)