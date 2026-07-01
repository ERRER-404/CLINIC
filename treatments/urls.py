from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TreatmentViewSet, MedicalRecordViewSet

router = DefaultRouter()
router.register('treatments', TreatmentViewSet, basename='treatment')
router.register('records', MedicalRecordViewSet, basename='medical-record')

urlpatterns = [
    path('', include(router.urls)),
]
