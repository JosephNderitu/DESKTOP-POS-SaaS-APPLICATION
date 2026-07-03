from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from .models import Product
from .serializers import ProductSerializer

class TenantProductViewSet(viewsets.ModelViewSet):
    """
    A multi-tenant secure endpoint that automatically handles fetching,
    creating, and modifying products inside an isolated store schema.
    """
    serializer_class = ProductSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        """Add request to serializer context for building full image URLs"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        # Only return active items for sale in the current tenant store
        return Product.objects.filter(is_active=True).order_by('name')