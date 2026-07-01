from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Treatment, TreatmentImage, MedicalRecord, MedicalRecordImage
from .serializers import (
    TreatmentSerializer, TreatmentImageSerializer,
    MedicalRecordSerializer, MedicalRecordImageSerializer
)
from accounts.permissions import IsDoctor, IsDoctorOrAdmin, IsClinicManagerOrAdmin, ReadOnly


class TreatmentViewSet(viewsets.ModelViewSet):
    serializer_class = TreatmentSerializer
    filterset_fields = ['category', 'clinic', 'doctors', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'name']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsClinicManagerOrAdmin()]
    
    def get_queryset(self):
        user = self.request.user
        qs = Treatment.objects.select_related('clinic').prefetch_related('images', 'doctors__user')
        
        if user.is_authenticated and user.role == 'CLINIC':
            try:
                clinic_id = user.clinic_manager_profile.clinic_id
                if clinic_id:
                    return qs.filter(clinic_id=clinic_id).order_by('name')
            except Exception:
                pass
            return qs.none()
        
        return qs.order_by('name')
    
    def create(self, request, *args, **kwargs):
        doctors = request.data.get('doctors', [])
        if not doctors:
            return Response({'error': 'Au moins un médecin est requis'}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        doctors = request.data.get('doctors', [])
        if not doctors:
            return Response({'error': 'Au moins un médecin est requis'}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)
        
        return qs.order_by('name')
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_image(self, request, pk=None):
        treatment = self.get_object()
        serializer = TreatmentImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(treatment=treatment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MedicalRecordViewSet(viewsets.ModelViewSet):
    serializer_class = MedicalRecordSerializer
    filterset_fields = ['patient', 'doctor', 'treatment']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [IsDoctorOrAdmin()]
    
    def get_queryset(self):
        user = self.request.user
        qs = MedicalRecord.objects.select_related('patient__user', 'doctor__user', 'treatment').order_by('-created_at')
        
        if user.role == 'DOCTOR':
            return qs.filter(doctor=user.doctor_profile)
        elif user.role == 'PATIENT':
            return qs.filter(patient=user.patient_profile)
        elif user.role == 'CLINIC':
            try:
                clinic_id = user.clinic_manager_profile.clinic_id
                if clinic_id:
                    return qs.filter(doctor__clinic_id=clinic_id)
            except Exception:
                pass
            return qs.none()
        return qs
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_image(self, request, pk=None):
        record = self.get_object()
        serializer = MedicalRecordImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(record=record)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
