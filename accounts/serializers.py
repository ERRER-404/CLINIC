from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import DoctorProfile, PatientProfile, ClinicManagerProfile

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True, min_length=6)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'password', 'password2', 'role', 'phone', 'date_of_birth']
    
    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        # Only PATIENT can self-register; ADMIN/DOCTOR/CLINIC are created by admins
        if data.get('role') in ('ADMIN', 'DOCTOR', 'CLINIC'):
            raise serializers.ValidationError({'role': 'This role cannot be self-registered.'})
        return data
    
    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        
        # Auto-create profile based on role
        if user.role == User.Role.DOCTOR:
            DoctorProfile.objects.create(user=user, specialization='General')
        elif user.role == User.Role.PATIENT:
            PatientProfile.objects.create(user=user)
        elif user.role == User.Role.CLINIC:
            ClinicManagerProfile.objects.create(user=user)
        
        return user


class AdminCreateUserSerializer(serializers.ModelSerializer):
    """Used by admins to create any user type including ADMIN/DOCTOR/CLINIC."""
    password = serializers.CharField(write_only=True, min_length=6)
    clinic_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'password', 'role', 'phone', 'date_of_birth', 'clinic_id']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        clinic_id = validated_data.pop('clinic_id', None)
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        
        if user.role == User.Role.DOCTOR:
            DoctorProfile.objects.create(user=user, specialization='General')
        elif user.role == User.Role.PATIENT:
            PatientProfile.objects.create(user=user)
        elif user.role == User.Role.CLINIC:
            profile = ClinicManagerProfile.objects.create(user=user)
            if clinic_id:
                from clinics.models import Clinic
                try:
                    clinic = Clinic.objects.get(id=clinic_id)
                    profile.clinic = clinic
                    profile.save()
                except Clinic.DoesNotExist:
                    pass
        
        return user


class UserSerializer(serializers.ModelSerializer):
    clinic_id = serializers.SerializerMethodField()
    clinic_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'phone', 'avatar', 'date_of_birth', 'date_joined',
                  'clinic_id', 'clinic_name']
        read_only_fields = ['id', 'date_joined', 'clinic_id', 'clinic_name']
    
    def get_clinic_id(self, obj):
        if obj.role == 'CLINIC' and hasattr(obj, 'clinic_manager_profile'):
            return obj.clinic_manager_profile.clinic_id
        if obj.role == 'DOCTOR' and hasattr(obj, 'doctor_profile') and obj.doctor_profile.clinic:
            return obj.doctor_profile.clinic_id
        return None
    
    def get_clinic_name(self, obj):
        if obj.role == 'CLINIC' and hasattr(obj, 'clinic_manager_profile') and obj.clinic_manager_profile.clinic:
            return obj.clinic_manager_profile.clinic.name
        if obj.role == 'DOCTOR' and hasattr(obj, 'doctor_profile') and obj.doctor_profile.clinic:
            return obj.doctor_profile.clinic.name
        return None


class DoctorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True, default='')
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = ['id', 'user', 'specialization', 'bio', 'experience_years',
                  'clinic', 'clinic_name', 'average_rating']

    def get_average_rating(self, obj):
        # Use cached rating if available (set in viewset query)
        if hasattr(obj, '_average_rating'):
            return obj._average_rating
        from reviews.models import Review
        from django.db.models import Avg
        avg = Review.objects.filter(doctor=obj).aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0


class PatientProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = PatientProfile
        fields = ['id', 'user', 'medical_history', 'allergies',
                  'blood_type', 'emergency_contact']


class ClinicManagerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True, default='')
    
    class Meta:
        model = ClinicManagerProfile
        fields = ['id', 'user', 'clinic', 'clinic_name']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=6)
