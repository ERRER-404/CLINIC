from rest_framework import serializers
from .models import Treatment, TreatmentImage, MedicalRecord, MedicalRecordImage


class TreatmentImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreatmentImage
        fields = ['id', 'image', 'is_before', 'caption', 'uploaded_at']


class TreatmentSerializer(serializers.ModelSerializer):
    images = TreatmentImageSerializer(many=True, read_only=True)
    average_rating = serializers.ReadOnlyField()
    doctor_name = serializers.SerializerMethodField()
    doctor_names = serializers.SerializerMethodField()
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    
    def get_doctor_name(self, obj):
        if obj.doctors.exists():
            return obj.doctors.first().user.get_full_name()
        return None
    
    def get_doctor_names(self, obj):
        return [d.user.get_full_name() for d in obj.doctors.all()]
    
    class Meta:
        model = Treatment
        fields = ['id', 'name', 'description', 'category', 'price',
                  'duration_minutes', 'sessions_count', 'clinic', 'doctors',
                  'clinic_name', 'doctor_name', 'doctor_names', 'is_active', 'average_rating',
                  'images', 'created_at']


class MedicalRecordImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecordImage
        fields = ['id', 'image', 'caption', 'uploaded_at']


class MedicalRecordSerializer(serializers.ModelSerializer):
    images = MedicalRecordImageSerializer(many=True, read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    treatment_name = serializers.CharField(source='treatment.name', read_only=True, default='')
    
    class Meta:
        model = MedicalRecord
        fields = ['id', 'patient', 'doctor', 'treatment', 'diagnosis', 'status', 'notes', 'prescription', 'recommendations',
                  'doctor_name', 'patient_name', 'treatment_name',
                  'images', 'created_at', 'updated_at']
