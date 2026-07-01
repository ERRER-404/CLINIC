from rest_framework import serializers
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    treatment_name = serializers.CharField(source='treatment.name', read_only=True, default='')
    
    class Meta:
        model = Review
        fields = ['id', 'doctor', 'treatment', 'rating', 'comment',
                  'patient_name', 'doctor_name', 'treatment_name', 'created_at']
        extra_kwargs = {
            'doctor': {'required': True},
            'treatment': {'required': False, 'allow_null': True},
            'rating': {'required': True},
            'comment': {'required': True},
        }
