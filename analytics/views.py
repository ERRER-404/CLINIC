from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from accounts.permissions import IsAdmin, IsDoctorOrAdmin, IsClinicManagerOrAdmin


class DashboardStatsView(APIView):
    """General dashboard statistics."""
    permission_classes = [IsClinicManagerOrAdmin | IsDoctorOrAdmin]
    
    def get(self, request):
        from accounts.models import User, DoctorProfile, PatientProfile
        from appointments.models import Appointment
        from billing.models import Invoice
        from treatments.models import Treatment
        
        user = request.user
        today = timezone.now().date()
        
        stats = {}
        
        if user.role == 'ADMIN':
            stats = {
                'total_patients': PatientProfile.objects.count(),
                'total_doctors': DoctorProfile.objects.count(),
                'total_treatments': Treatment.objects.count(),
                'total_appointments': Appointment.objects.count(),
                'pending_appointments': Appointment.objects.filter(status='PENDING').count(),
                'today_appointments': Appointment.objects.filter(date=today).count(),
                'total_revenue': float(Invoice.objects.filter(status='PAID').aggregate(
                    total=Sum('total'))['total'] or 0),
                'unpaid_invoices': Invoice.objects.filter(status='UNPAID').count(),
            }
        elif user.role == 'CLINIC':
            try:
                clinic_id = user.clinic_manager_profile.clinic_id
                if clinic_id:
                    stats = {
                        'total_patients': Appointment.objects.filter(clinic_id=clinic_id).values('patient').distinct().count(),
                        'total_doctors': DoctorProfile.objects.filter(clinic_id=clinic_id).count(),
                        'total_appointments': Appointment.objects.filter(clinic_id=clinic_id).count(),
                        'pending_appointments': Appointment.objects.filter(clinic_id=clinic_id, status='PENDING').count(),
                        'today_appointments': Appointment.objects.filter(clinic_id=clinic_id, date=today).count(),
                        'completed_appointments': Appointment.objects.filter(clinic_id=clinic_id, status='COMPLETED').count(),
                        'total_revenue': float(Invoice.objects.filter(
                            appointment__clinic_id=clinic_id, status='PAID'
                        ).aggregate(total=Sum('total'))['total'] or 0),
                        'unpaid_invoices': Invoice.objects.filter(
                            appointment__clinic_id=clinic_id, status='UNPAID'
                        ).count(),
                    }
                else:
                    stats = {}
            except Exception:
                stats = {}
        elif user.role == 'DOCTOR':
            doctor = user.doctor_profile
            stats = {
                'total_patients': Appointment.objects.filter(doctor=doctor).values('patient').distinct().count(),
                'total_appointments': Appointment.objects.filter(doctor=doctor).count(),
                'pending_appointments': Appointment.objects.filter(doctor=doctor, status='PENDING').count(),
                'today_appointments': Appointment.objects.filter(doctor=doctor, date=today).count(),
                'completed_appointments': Appointment.objects.filter(doctor=doctor, status='COMPLETED').count(),
                'total_revenue': float(Invoice.objects.filter(
                    appointment__doctor=doctor, status='PAID'
                ).aggregate(total=Sum('total'))['total'] or 0),
            }
        
        return Response(stats)


class RevenueChartView(APIView):
    """Revenue data grouped by month."""
    permission_classes = [IsClinicManagerOrAdmin | IsDoctorOrAdmin]

    def get(self, request):
        from billing.models import Invoice

        try:
            months = min(max(int(request.query_params.get('months', 12)), 1), 60)
        except (TypeError, ValueError):
            months = 12

        start_date = timezone.now() - timedelta(days=months * 30)

        queryset = Invoice.objects.filter(status='PAID', created_at__gte=start_date)

        if request.user.role == 'DOCTOR':
            queryset = queryset.filter(appointment__doctor=request.user.doctor_profile)
        elif request.user.role == 'CLINIC':
            try:
                clinic_id = request.user.clinic_manager_profile.clinic_id
                if clinic_id:
                    queryset = queryset.filter(appointment__clinic_id=clinic_id)
            except Exception:
                queryset = queryset.none()

        data = queryset.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            revenue=Sum('total'),
            count=Count('id')
        ).order_by('month')

        return Response(list(data))


class TopTreatmentsView(APIView):
    """Most popular treatments by appointment count."""
    permission_classes = [IsDoctorOrAdmin]

    def get(self, request):
        from appointments.models import Appointment
        from django.db.models import Q

        # Validate and cap limit to prevent abuse
        try:
            limit = min(max(int(request.query_params.get('limit', 10)), 1), 50)
        except (TypeError, ValueError):
            limit = 10

        queryset = Appointment.objects.filter(
            treatment__isnull=False
        ).select_related('treatment', 'invoice')

        if request.user.role == 'DOCTOR':
            queryset = queryset.filter(doctor=request.user.doctor_profile)

        data = queryset.values(
            'treatment__name', 'treatment__category'
        ).annotate(
            count=Count('id'),
            revenue=Sum('invoice__total')
        ).order_by('-count')[:limit]

        return Response(list(data))


class PatientGrowthView(APIView):
    """Patient registration growth over time."""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        from accounts.models import User
        
        data = User.objects.filter(
            role='PATIENT'
        ).annotate(
            month=TruncMonth('date_joined')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        return Response(list(data))
