from rest_framework import serializers
from .models import Product, Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class ProductSerializer(serializers.ModelSerializer):
    # Bring in the category details as a nested object, read-only for now
    category_detail = CategorySerializer(source='category', read_only=True)
    
    # Add discount field that matches what dashboard expects
    discount_percent = serializers.DecimalField(
        source='product_discount', 
        max_digits=5, 
        decimal_places=2,
        read_only=True
    )
    
    # Add image URL field
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 
            'category', 
            'category_detail',
            'name', 
            'sku', 
            'description', 
            'cost_price', 
            'selling_price',
            'product_discount',  # Keep original field
            'discount_percent',  # Add alias for dashboard
            'stock_quantity', 
            'low_stock_threshold', 
            'is_active',
            'image_url'  # Add image URL
        ]
    
    def get_image_url(self, obj):
        """Get the full URL for the product image"""
        if obj.product_image and hasattr(obj.product_image, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.product_image.url)
            return obj.product_image.url
        return None