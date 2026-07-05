"""
URL configuration for core_backend project (public schema).

This urlconf is only reachable via the base domain (localhost:8000), never
via a tenant subdomain (store1.localhost:8000 uses tenant_urls.py instead).
That's what keeps Django admin — and these platform-owner endpoints — out of
reach of store-level staff accounts.

For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from tenants.platform_views import (
    TenantListView,
    TenantReactivateView,
    TenantRenameDomainView,
    TenantSuspendView,
    TenantTerminateView,
    TenantUserListView,
    TenantUserSuspendView,
)
from tenants.views import TenantRegistrationView
from users.views import POSLoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    # POS Desktop Endpoint Interface
    path('api/v1/login/', POSLoginView.as_view(), name='pos_login'),
    path('api/v1/register/', TenantRegistrationView.as_view(), name='pos_register'),

    # Platform owner — "God's eye" store management
    # All views here are locked to IsPlatformOwner (see tenants/permissions.py)
    path('api/v1/platform/stores/', TenantListView.as_view(), name='platform_store_list'),
    path('api/v1/platform/stores/<str:schema_name>/suspend/', TenantSuspendView.as_view(), name='platform_store_suspend'),
    path('api/v1/platform/stores/<str:schema_name>/reactivate/', TenantReactivateView.as_view(), name='platform_store_reactivate'),
    path('api/v1/platform/stores/<str:schema_name>/terminate/', TenantTerminateView.as_view(), name='platform_store_terminate'),
    path('api/v1/platform/stores/<str:schema_name>/rename-domain/', TenantRenameDomainView.as_view(), name='platform_store_rename_domain'),
    path('api/v1/platform/stores/<str:schema_name>/users/', TenantUserListView.as_view(), name='platform_store_users'),
    path('api/v1/platform/stores/<str:schema_name>/users/<int:user_id>/suspend/', TenantUserSuspendView.as_view(), name='platform_store_user_suspend'),
]

# Serve media files for tenant domains in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)