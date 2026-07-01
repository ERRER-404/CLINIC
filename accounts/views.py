from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import (
    RegisterSerializer, UserSerializer, DoctorProfileSerializer,
    PatientProfileSerializer, ClinicManagerProfileSerializer,
    ChangePasswordSerializer, AdminCreateUserSerializer
)
from .models import DoctorProfile, PatientProfile, ClinicManagerProfile
from .permissions import IsAdmin, IsOwnerOrAdmin, IsClinicManager, IsDoctor

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Register a new user (patients only via public form)."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class ProfileView(APIView):
    """Get or update current user profile."""
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get(self, request):
        user = request.user
        data = UserSerializer(user, context={'request': request}).data
        
        if user.role == 'DOCTOR' and hasattr(user, 'doctor_profile'):
            data['doctor_profile'] = DoctorProfileSerializer(user.doctor_profile).data
        elif user.role == 'PATIENT' and hasattr(user, 'patient_profile'):
            data['patient_profile'] = PatientProfileSerializer(user.patient_profile).data
        elif user.role == 'CLINIC' and hasattr(user, 'clinic_manager_profile'):
            data['clinic_manager_profile'] = ClinicManagerProfileSerializer(user.clinic_manager_profile).data
        
        return Response(data)
    
    def patch(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DoctorProfileUpdateView(APIView):
    """Update doctor profile details."""
    
    def patch(self, request):
        if request.user.role != 'DOCTOR':
            return Response({'error': 'Not a doctor'}, status=403)
        
        profile = request.user.doctor_profile
        serializer = DoctorProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DoctorProfileAssignView(APIView):
    """Assign a doctor to a clinic (Admin or Clinic Manager only)."""
    
    def patch(self, request, doctor_id):
        if request.user.role not in ['ADMIN', 'CLINIC']:
            return Response({'error': 'Permission denied'}, status=403)
        
        try:
            profile = DoctorProfile.objects.get(id=doctor_id)
        except DoctorProfile.DoesNotExist:
            return Response({'error': 'Doctor profile not found'}, status=404)
        
        # If clinic manager, verify they can only assign to their own clinic
        if request.user.role == 'CLINIC':
            clinic_id = request.user.clinic_manager_profile.clinic_id
            if not clinic_id:
                return Response({'error': 'No clinic assigned'}, status=400)
            new_clinic_id = request.data.get('clinic')
            if new_clinic_id and int(new_clinic_id) != clinic_id:
                return Response({'error': 'Cannot assign to different clinic'}, status=403)
        
        serializer = DoctorProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PatientProfileUpdateView(APIView):
    """Update patient profile details."""
    
    def patch(self, request):
        if request.user.role != 'PATIENT':
            return Response({'error': 'Not a patient'}, status=403)
        
        profile = request.user.patient_profile
        serializer = PatientProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ClinicManagerProfileUpdateView(APIView):
    """Update clinic manager profile details."""
    
    def patch(self, request):
        if request.user.role != 'CLINIC':
            return Response({'error': 'Not a clinic manager'}, status=403)
        
        profile = request.user.clinic_manager_profile
        serializer = ClinicManagerProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """Change user password."""
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if not request.user.check_password(serializer.data['old_password']):
            return Response({'error': 'Incorrect old password'}, status=400)
        
        request.user.set_password(serializer.data['new_password'])
        request.user.save()
        return Response({'message': 'Password changed successfully'})


class UserListView(generics.ListCreateAPIView):
    """List all users or create a new user (Admin only)."""
    queryset = User.objects.select_related().all().order_by('-date_joined')
    permission_classes = [IsAdmin]
    filterset_fields = ['role']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AdminCreateUserSerializer
        return UserSerializer


class DoctorListView(generics.ListAPIView):
    """List all doctors (public)."""
    serializer_class = DoctorProfileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        from django.db.models import Avg, Prefetch
        from reviews.models import Review

        return DoctorProfile.objects.select_related('user', 'clinic').annotate(
            _average_rating=Avg('reviews__rating')
        ).prefetch_related('reviews').order_by('user__last_name', 'user__first_name')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ClinicPatientsListView(generics.ListAPIView):
    """List patients that have booked an appointment at the manager's clinic."""
    serializer_class = PatientProfileSerializer
    permission_classes = [IsClinicManager]
    
    def get_queryset(self):
        user = self.request.user
        try:
            clinic_id = user.clinic_manager_profile.clinic_id
            if not clinic_id:
                return PatientProfile.objects.none()
            
            from appointments.models import Appointment
            patient_ids = Appointment.objects.filter(clinic_id=clinic_id).values_list('patient_id', flat=True).distinct()
            return PatientProfile.objects.filter(id__in=patient_ids).select_related('user').order_by('user__last_name', 'user__first_name')
        except Exception:
            return PatientProfile.objects.none()


class DoctorPatientsView(generics.ListAPIView):
    """List patients that have had appointments with this doctor."""
    serializer_class = PatientProfileSerializer
    permission_classes = [IsDoctor]
    
    def get_queryset(self):
        user = self.request.user
        try:
            doctor_id = user.doctor_profile.id
            if not doctor_id:
                return PatientProfile.objects.none()
            
            from appointments.models import Appointment
            patient_ids = Appointment.objects.filter(doctor_id=doctor_id).values_list('patient_id', flat=True).distinct()
            return PatientProfile.objects.filter(id__in=patient_ids).select_related('user').order_by('user__last_name', 'user__first_name')
        except Exception:
            return PatientProfile.objects.none()


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: manage individual users."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance == request.user:
            return Response({'error': 'You cannot delete your own account.'}, status=400)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
