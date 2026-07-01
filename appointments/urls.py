from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet, TimeSlotViewSet

router = DefaultRouter()
router.register('appointments', AppointmentViewSet, basename='appointment')
router.register('time-slots', TimeSlotViewSet, basename='time-slot')

urlpatterns = [
    path('', include(router.urls)),
]
