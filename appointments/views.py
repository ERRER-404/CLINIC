from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, date
from .models import Appointment, TimeSlot
from .serializers import AppointmentSerializer, TimeSlotSerializer
from accounts.permissions import IsDoctor, IsDoctorOrAdmin, IsPatient

# Tax rate configuration
DEFAULT_TAX_RATE = 0.19  # 19% VAT


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    filterset_fields = ['status', 'doctor', 'patient', 'clinic', 'date']
    ordering_fields = ['date', 'time', 'created_at']

    def get_permissions(self):
        if self.action == 'create':
            return [IsPatient()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Validate date is not in the past
        appointment_date = serializer.validated_data.get('date')
        if appointment_date and appointment_date < date.today():
            return Response(
                {'error': 'Cannot book appointments in the past'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            self.perform_create(serializer)
        except ValidationError as e:
            error_msg = str(e.message_dict) if hasattr(e, 'message_dict') else str(e)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.select_related(
            'patient__user', 'doctor__user', 'treatment', 'clinic'
        ).order_by('-date', '-time')
        
        if user.role == 'DOCTOR':
            return qs.filter(doctor=user.doctor_profile)
        elif user.role == 'PATIENT':
            return qs.filter(patient=user.patient_profile)
        elif user.role == 'CLINIC':
            try:
                clinic_id = user.clinic_manager_profile.clinic_id
                return qs.filter(clinic_id=clinic_id) if clinic_id else qs.none()
            except Exception:
                return qs.none()
        return qs
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        appointment = self.get_object()
        if request.user.role not in ['ADMIN', 'CLINIC']:
            return Response({'error': 'Only admin or clinic manager can approve appointments'}, status=403)
        if appointment.status != Appointment.Status.PENDING:
            return Response({'error': 'Only pending appointments can be approved'}, status=400)
        appointment.status = Appointment.Status.APPROVED
        appointment.save()
        return Response(AppointmentSerializer(appointment).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        appointment = self.get_object()
        if request.user.role not in ['DOCTOR', 'ADMIN', 'CLINIC']:
            return Response({'error': 'Permission denied'}, status=403)
        if appointment.status != Appointment.Status.APPROVED:
            return Response({'error': 'Only approved appointments can be completed'}, status=400)
        
        products_used = request.data.get('products_used', [])
        
        from inventory.models import Product, StockTransaction
        for item in products_used:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 1)
            try:
                product = Product.objects.get(id=product_id, clinic=appointment.clinic)
                if product.quantity >= quantity:
                    product.quantity -= quantity
                    product.save()
                    StockTransaction.objects.create(
                        product=product,
                        transaction_type=StockTransaction.TransactionType.OUT,
                        quantity_change=-quantity,
                        reason=f'Traitement #{appointment.id} - {appointment.treatment.name if appointment.treatment else "N/A"}',
                        created_by=request.user,
                    )
                else:
                    return Response({'error': f'Stock insuffisant pour {product.name}'}, status=400)
            except Product.DoesNotExist:
                pass
        
        appointment.status = Appointment.Status.COMPLETED
        appointment.save()

        from billing.models import Invoice
        if not hasattr(appointment, 'invoice'):
            product_cost = sum(
                item.get('quantity', 1) * Product.objects.get(id=item['product_id']).price_per_unit
                for item in products_used if Product.objects.filter(id=item['product_id']).exists()
            )
            treatment_price = float(appointment.treatment.price) if appointment.treatment else 0
            price = treatment_price + float(product_cost)
            total = price
            Invoice.objects.create(
                appointment=appointment,
                amount=price,
                tax=0,
                total=total,
            )

        return Response(AppointmentSerializer(appointment).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        # Only the patient who owns it, the assigned doctor, or admin can cancel
        user = request.user
        if user.role == 'PATIENT' and appointment.patient != user.patient_profile:
            return Response({'error': 'You can only cancel your own appointments'}, status=403)
        if user.role == 'DOCTOR' and appointment.doctor != user.doctor_profile:
            return Response({'error': 'You can only cancel your own appointments'}, status=403)
        if appointment.status in [Appointment.Status.COMPLETED, Appointment.Status.CANCELLED]:
            return Response({'error': 'Cannot cancel a completed or already cancelled appointment'}, status=400)
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()
        return Response(AppointmentSerializer(appointment).data)
    
    @action(detail=False, methods=['get'])
    def available_slots(self, request):
        """Get available time slots for a doctor on a given date."""
        doctor_id = request.query_params.get('doctor_id')
        date = request.query_params.get('date')
        
        if not doctor_id or not date:
            return Response({'error': 'doctor_id and date are required'}, status=400)
        
        from datetime import datetime
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        day_of_week = date_obj.weekday()
        
        # Get doctor's time slots for the day
        slots = TimeSlot.objects.filter(
            doctor_id=doctor_id, day_of_week=day_of_week, is_available=True
        )
        
        # Get booked times
        booked = Appointment.objects.filter(
            doctor_id=doctor_id, date=date_obj,
            status__in=['PENDING', 'APPROVED']
        ).values_list('time', flat=True)
        
        available = []
        for slot in slots:
            if slot.start_time not in booked:
                available.append(TimeSlotSerializer(slot).data)
        
        return Response(available)


class TimeSlotViewSet(viewsets.ModelViewSet):
    serializer_class = TimeSlotSerializer
    permission_classes = [IsDoctorOrAdmin]
    filterset_fields = ['doctor', 'day_of_week', 'is_available']
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'DOCTOR':
            return TimeSlot.objects.filter(doctor=user.doctor_profile)
        return TimeSlot.objects.all()
