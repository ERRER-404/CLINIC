from rest_framework import serializers
from .models import Product, StockTransaction


class ProductSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'category', 'quantity', 'unit',
                  'min_stock_alert', 'clinic', 'price_per_unit',
                  'is_low_stock', 'created_at']


class StockTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, default='')
    
    class Meta:
        model = StockTransaction
        fields = ['id', 'product', 'product_name', 'transaction_type',
                  'quantity_change', 'reason', 'created_at', 'created_by',
                  'created_by_name']
        read_only_fields = ['created_by']
