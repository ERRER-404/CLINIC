import stripe
import hashlib
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from .models import Invoice
from .serializers import InvoiceSerializer
from accounts.permissions import IsDoctorOrAdmin, IsClinicManagerOrAdmin

stripe.api_key = settings.STRIPE_SECRET_KEY


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'total']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()] # Manual role checks in action methods
    
    def get_queryset(self):
        user = self.request.user
        qs = Invoice.objects.select_related(
            'appointment__patient__user',
            'appointment__doctor__user',
            'appointment__treatment',
            'appointment__clinic'
        ).order_by('-created_at')
        
        if user.role == 'DOCTOR':
            if hasattr(user, 'doctor_profile'):
                return qs.filter(appointment__doctor=user.doctor_profile)
            return qs.none()
        elif user.role == 'PATIENT':
            if hasattr(user, 'patient_profile'):
                return qs.filter(appointment__patient=user.patient_profile)
            return qs.none()
        elif user.role == 'CLINIC':
            try:
                clinic_id = user.clinic_manager_profile.clinic_id
                return qs.filter(appointment__clinic_id=clinic_id) if clinic_id else qs.none()
            except Exception:
                return qs.none()
        return qs
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        if request.user.role not in ['DOCTOR', 'ADMIN', 'CLINIC']:
            return Response({'error': 'Permission denied'}, status=403)
        invoice = self.get_object()
        invoice.status = Invoice.Status.PAID
        invoice.payment_method = request.data.get('payment_method', 'Espèce')
        invoice.paid_at = timezone.now()
        invoice.save()
        return Response(InvoiceSerializer(invoice).data)
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        if request.user.role not in ['DOCTOR', 'ADMIN', 'CLINIC']:
            return Response({'error': 'Permission denied'}, status=403)
        invoice = self.get_object()
        invoice.status = Invoice.Status.REFUNDED
        invoice.save()
        return Response(InvoiceSerializer(invoice).data)
    
    @action(detail=True, methods=['post'])
    def create_payment_intent(self, request, pk=None):
        """Create a Stripe PaymentIntent for this invoice."""
        if request.user.role not in ['PATIENT', 'ADMIN', 'CLINIC', 'DOCTOR']:
            return Response({'error': 'Permission denied'}, status=403)
        
        invoice = self.get_object()
        if invoice.status == Invoice.Status.PAID:
            return Response({'error': 'Invoice already paid'}, status=400)
        
        amount_cents = int(float(invoice.total) * 100)
        
        if amount_cents < 50:
            return Response({'error': 'Le montant minimum est 0.50 DT'}, status=400)
        
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                metadata={
                    'invoice_id': str(invoice.id),
                    'appointment_id': str(invoice.appointment_id),
                },
            )
            invoice.stripe_payment_intent_id = intent.id
            invoice.save()
            return Response({
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
            })
        except stripe.StripeError as e:
            return Response({'error': str(e)}, status=400)
    
    @action(detail=True, methods=['post'])
    def confirm_payment(self, request, pk=None):
        """Confirm payment after Stripe checkout completion."""
        if request.user.role not in ['PATIENT', 'ADMIN', 'CLINIC', 'DOCTOR']:
            return Response({'error': 'Permission denied'}, status=403)
        
        invoice = self.get_object()
        payment_intent_id = request.data.get('payment_intent_id')
        
        if not payment_intent_id:
            return Response({'error': 'payment_intent_id required'}, status=400)
        
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if intent.status == 'succeeded':
                invoice.status = Invoice.Status.PAID
                invoice.payment_method = 'Carte Bancaire'
                invoice.paid_at = timezone.now()
                invoice.stripe_payment_intent_id = payment_intent_id
                invoice.save()
                return Response(InvoiceSerializer(invoice).data)
            elif intent.status == 'requires_payment_method':
                return Response({'error': 'Payment failed, please try again'}, status=400)
            else:
                return Response({'error': f'Payment status: {intent.status}'}, status=400)
        except stripe.StripeError as e:
            return Response({'error': str(e)}, status=400)
    
    @action(detail=True, methods=['get'])
    def generate_pdf(self, request, pk=None):
        """Generate a downloadable PDF invoice with fingerprint verification."""
        invoice = self.get_object()
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="facture_{invoice.id}.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=A4, topMargin=40, bottomMargin=40)
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, spaceAfter=30, alignment=1)
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=14, spaceBefore=20, spaceAfter=10)
        normal_style = styles['Normal']
        
        elements.append(Paragraph("FACTURE", title_style))
        elements.append(Spacer(1, 20))
        
        clinic = invoice.appointment.clinic
        patient = invoice.appointment.patient.user
        doctor = invoice.appointment.doctor.user if invoice.appointment.doctor else None
        treatment = invoice.appointment.treatment
        
        clinic_info = ""
        if clinic:
            clinic_info = f"<b>Clinique:</b> {clinic.name}<br/>{clinic.address or ''}<br/>"
        else:
            clinic_info = "<b>Clinique:</b> N/A<br/>"
        elements.append(Paragraph(clinic_info, normal_style))
        elements.append(Spacer(1, 20))
        
        patient_name = patient.get_full_name() or patient.username or 'N/A'
        elements.append(Paragraph(f"<b>Facture N°:</b> {invoice.id}", normal_style))
        elements.append(Paragraph(f"<b>Date:</b> {invoice.created_at.strftime('%d/%m/%Y')}", normal_style))
        elements.append(Paragraph(f"<b>Patient:</b> {patient_name}", normal_style))
        elements.append(Paragraph(f"<b>Téléphone:</b> {patient.phone or 'N/A'}", normal_style))
        if doctor:
            doctor_name = doctor.get_full_name() or doctor.username
            elements.append(Paragraph(f"<b>Médecin:</b> {doctor_name}", normal_style))
        elements.append(Spacer(1, 20))
        
        treatment_name = treatment.name if treatment else 'N/A'
        data = [
            ['Description', 'Montant'],
            [f'Traitement: {treatment_name}', f'{invoice.amount} DT'],
            [f'TVA (19%)', f'{invoice.tax} DT'],
            ['TOTAL', f'{invoice.total} DT'],
        ]
        t = Table(data, colWidths=[300, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 30))
        
        status_label = 'Payée' if invoice.status == 'PAID' else 'Non Payée' if invoice.status == 'UNPAID' else 'Remboursée'
        payment_method = invoice.payment_method or 'N/A'
        
        elements.append(Paragraph(f"<b>Statut:</b> {status_label}", normal_style))
        elements.append(Paragraph(f"<b>Mode de Paiement:</b> {payment_method}", normal_style))
        if invoice.paid_at:
            elements.append(Paragraph(f"<b>Date de Paiement:</b> {invoice.paid_at.strftime('%d/%m/%Y')}", normal_style))
        elements.append(Spacer(1, 30))
        
        elements.append(Paragraph("<b>Vérification d'authenticité</b>", heading_style))
        elements.append(Paragraph(f"<b>Empreinte:</b> <font size='8'>{invoice.fingerprint}</font>", normal_style))
        
        verify_data = f"{invoice.id}-{invoice.total}-{invoice.created_at}-{invoice.fingerprint}"
        verify_hash = hashlib.sha256(verify_data.encode()).hexdigest()[:16]
        elements.append(Paragraph(f"<b>Code de Vérification:</b> {verify_hash}", normal_style))
        
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("<i>Ce document est généré automatiquement par AesthetiCare.</i>", normal_style))
        
        doc.build(elements)
        return response
