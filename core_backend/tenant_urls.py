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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)