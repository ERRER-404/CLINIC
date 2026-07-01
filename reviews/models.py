from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    """Patient review for a treatment/doctor."""
    patient = models.ForeignKey(
        'accounts.PatientProfile', on_delete=models.CASCADE, related_name='reviews'
    )
    doctor = models.ForeignKey(
        'accounts.DoctorProfile', on_delete=models.CASCADE, related_name='reviews'
    )
    treatment = models.ForeignKey(
        'treatments.Treatment', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviews'
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['patient', 'doctor', 'treatment']
    
    def __str__(self):
        return f"Review by {self.patient} — {self.rating}/5"
