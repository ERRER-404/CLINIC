from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import models
from .models import Product, StockTransaction
from .serializers import ProductSerializer, StockTransactionSerializer
from accounts.permissions import IsClinicStaffOrAdmin


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsClinicStaffOrAdmin]
    filterset_fields = ['category', 'clinic']
    search_fields = ['name']
    ordering_fields = ['name', 'quantity', 'price_per_unit']

    def get_queryset(self):
        user = self.request.user
        qs = Product.objects.select_related('clinic').all().order_by('name')
        if user.role == 'CLINIC':
            try:
                clinic_id = user.clinic_manager_profile.clinic_id
                return qs.filter(clinic_id=clinic_id) if clinic_id else qs.none()
            except Exception:
                return qs.none()
        return qs

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get products with low stock levels - optimized with DB query."""
        qs = self.get_queryset()
        low = qs.filter(quantity__lte=models.F('min_stock_alert'))
        serializer = ProductSerializer(low, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_stock(self, request, pk=None):
        """Add stock to a product."""
        product = self.get_object()

        # Validate quantity - must be positive integer
        try:
            quantity = int(request.data.get('quantity', 0))
        except (TypeError, ValueError):
            return Response({'error': 'Quantity must be a valid integer'}, status=400)

        if quantity <= 0:
            return Response({'error': 'Quantity must be positive'}, status=400)

        if quantity > 10000:  # Prevent bulk additions abuse
            return Response({'error': 'Quantity cannot exceed 10,000 per transaction'}, status=400)

        product.quantity += quantity
        product.save()

        StockTransaction.objects.create(
            product=product,
            transaction_type='IN',
            quantity_change=quantity,
            reason=request.data.get('reason', 'Stock replenishment'),
            created_by=request.user
        )

        return Response(ProductSerializer(product).data)

    @action(detail=True, methods=['post'])
    def use_stock(self, request, pk=None):
        """Use (deduct) stock from a product."""
        product = self.get_object()

        # Validate quantity - must be positive integer
        try:
            quantity = int(request.data.get('quantity', 0))
        except (TypeError, ValueError):
            return Response({'error': 'Quantity must be a valid integer'}, status=400)

        if quantity <= 0:
            return Response({'error': 'Quantity must be positive'}, status=400)

        if quantity > 1000:  # Prevent bulk usage abuse
            return Response({'error': 'Quantity cannot exceed 1,000 per transaction'}, status=400)

        if product.quantity < quantity:
            return Response({'error': f'Insufficient stock. Available: {product.quantity}'}, status=400)

        product.quantity -= quantity
        product.save()

        StockTransaction.objects.create(
            product=product,
            transaction_type='OUT',
            quantity_change=-quantity,
            reason=request.data.get('reason', 'Used in treatment'),
            created_by=request.user
        )

        return Response(ProductSerializer(product).data)


class StockTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockTransactionSerializer
    permission_classes = [IsClinicStaffOrAdmin]
    filterset_fields = ['product', 'transaction_type']
    
    def get_queryset(self):
        user = self.request.user
        qs = StockTransaction.objects.select_related('product', 'created_by').all().order_by('-created_at')
        if user.role == 'CLINIC':
            try:
                clinic_id = user.clinic_manager_profile.clinic_id
                return qs.filter(product__clinic_id=clinic_id) if clinic_id else qs.none()
            except Exception:
                return qs.none()
        return qs
