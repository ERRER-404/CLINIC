from django.db import models


class Product(models.Model):
    """Inventory product for a clinic."""
    
    class Category(models.TextChoices):
        BOTOX = 'BOTOX', 'Botox'
        FILLER = 'FILLER', 'Dermal Filler'
        LASER = 'LASER', 'Laser Equipment'
        SKINCARE = 'SKINCARE', 'Skincare Product'
        CONSUMABLE = 'CONSUMABLE', 'Consumable'
        OTHER = 'OTHER', 'Other'
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices)
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=50, default='units')
    min_stock_alert = models.PositiveIntegerField(default=5, help_text='Alert when stock falls below')
    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.CASCADE, related_name='products'
    )
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.min_stock_alert


class StockTransaction(models.Model):
    """Track stock changes."""
    
    class TransactionType(models.TextChoices):
        IN = 'IN', 'Stock In'
        OUT = 'OUT', 'Stock Out'
        ADJUSTMENT = 'ADJUSTMENT', 'Adjustment'
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=15, choices=TransactionType.choices)
    quantity_change = models.IntegerField()
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True
    )
    
    def __str__(self):
        return f"{self.transaction_type}: {self.quantity_change} × {self.product.name}"
