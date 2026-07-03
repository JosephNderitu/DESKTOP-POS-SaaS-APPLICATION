# core_backend/tenant_urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import POSLoginView
from inventory.views import TenantProductViewSet

# Create a clean REST router mapping for tenant apps
tenant_router = DefaultRouter()
tenant_router.register(r'products', TenantProductViewSet, basename='tenant-products')

#SERVING STATIC AND MEDIA FILES IN DEVELOPMENT
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Fallback to standard admin portal walled within this specific tenant
    path('admin/', admin.site.urls),
    
    # Store actions (Login works inside tenant schemas too)
    path('api/v1/login/', POSLoginView.as_view(), name='pos_login'),
    
    # Dynamic Product Feed Engine route: api/v1/inventory/products/
    path('api/v1/inventory/', include(tenant_router.urls)),
]
# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)