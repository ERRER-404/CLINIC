from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, StockTransactionViewSet

router = DefaultRouter()
router.register('products', ProductViewSet, basename='product')
router.register('transactions', StockTransactionViewSet, basename='stock-transaction')

urlpatterns = [
    path('', include(router.urls)),
]
