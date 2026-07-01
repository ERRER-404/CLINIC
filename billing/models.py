import hashlib
import uuid
from django.db import models


class Invoice(models.Model):
    
    class Status(models.TextChoices):
        UNPAID = 'UNPAID', 'Unpaid'
        PAID = 'PAID', 'Paid'
        REFUNDED = 'REFUNDED', 'Refunded'
    
    appointment = models.OneToOneField(
        'appointments.Appointment', on_delete=models.CASCADE, related_name='invoice'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNPAID)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    fingerprint = models.CharField(max_length=64, blank=True, null=True, unique=True)
    
    def __str__(self):
        return f"Invoice #{self.pk} — {self.total} DT ({self.status})"
    
    def generate_fingerprint(self):
        data = f"{self.id}-{self.appointment_id}-{self.total}-{self.created_at}-{uuid.uuid4()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def save(self, *args, **kwargs):
        if not self.total:
            self.total = self.amount + self.tax
        if not self.fingerprint:
            self.fingerprint = self.generate_fingerprint()
        super().save(*args, **kwargs)
