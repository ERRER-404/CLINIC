from rest_framework import serializers
from django.utils import timezone
from .models import Appointment, TimeSlot


class TimeSlotSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = TimeSlot
        fields = ['id', 'doctor', 'day_of_week', 'day_name',
                  'start_time', 'end_time', 'is_available']


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    treatment_name = serializers.CharField(source='treatment.name', read_only=True, default='')
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    
    class Meta:
        model = Appointment
        fields = ['id', 'patient', 'doctor', 'treatment', 'clinic',
                  'patient_name', 'doctor_name', 'treatment_name', 'clinic_name',
                  'date', 'time', 'status', 'notes', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate appointment data."""
        doctor = data.get('doctor')
        clinic = data.get('clinic')
        date = data.get('date')
        time = data.get('time')
        
        # Reject past dates
        if date and date < timezone.now().date():
            raise serializers.ValidationError({'date': 'Cannot book appointments in the past.'})
        
        # Verify doctor belongs to selected clinic
        if doctor and clinic and doctor.clinic_id != clinic.id:
            raise serializers.ValidationError({'doctor': 'This doctor does not belong to the selected clinic.'})
        
        # Check for overlapping appointments
        if doctor and date and time:
            overlapping = Appointment.objects.filter(
                doctor=doctor, date=date, time=time,
                status__in=['PENDING', 'APPROVED']
            )
            if self.instance:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise serializers.ValidationError('This time slot is already booked.')
        
        return data
