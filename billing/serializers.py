from rest_framework import serializers
from .models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='appointment.patient.user.get_full_name', read_only=True
    )
    treatment_name = serializers.CharField(
        source='appointment.treatment.name', read_only=True, default=''
    )
    doctor_name = serializers.CharField(
        source='appointment.doctor.user.get_full_name', read_only=True
    )
    clinic_name = serializers.CharField(
        source='appointment.clinic.name', read_only=True, default=''
    )
    
    class Meta:
        model = Invoice
        fields = ['id', 'appointment', 'amount', 'tax', 'total', 'status', 'payment_method',
                  'notes', 'patient_name', 'treatment_name', 'doctor_name', 'clinic_name',
                  'stripe_payment_intent_id', 'fingerprint', 'created_at', 'paid_at']
