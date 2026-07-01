from django.contrib import admin
from .models import Product, StockTransaction

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'quantity', 'unit', 'is_low_stock', 'clinic']
    list_filter = ['category', 'clinic']
    search_fields = ['name']

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['product', 'transaction_type', 'quantity_change', 'created_at', 'created_by']
    list_filter = ['transaction_type']
