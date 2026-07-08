from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from .models import Product
from .serializers import ProductSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

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
    
    @action(detail=False, methods=['get'], url_path='lookup')
    def lookup(self, request):
        """
        GET /api/products/lookup/?code=<sku>
        Resolves a scanned barcode/SKU to a single product. Kept separate
        from the list endpoint so the desktop client can hit it directly
        on a cache-miss without pulling the whole catalog.
        """
        code = request.query_params.get('code', '').strip()
        if not code:
            return Response({"detail": "code parameter required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(sku__iexact=code, is_active=True)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(product)
        return Response(serializer.data)