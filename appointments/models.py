from django.db import models
from django.core.exceptions import ValidationError


class TimeSlot(models.Model):
    """Available time slots for a doctor."""
    
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, 'Monday'
        TUESDAY = 1, 'Tuesday'
        WEDNESDAY = 2, 'Wednesday'
        THURSDAY = 3, 'Thursday'
        FRIDAY = 4, 'Friday'
        SATURDAY = 5, 'Saturday'
        SUNDAY = 6, 'Sunday'
    
    doctor = models.ForeignKey(
        'accounts.DoctorProfile', on_delete=models.CASCADE, related_name='time_slots'
    )
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"Dr. {self.doctor.user.last_name} — {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class Appointment(models.Model):
    """Patient appointment with a doctor."""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    patient = models.ForeignKey(
        'accounts.PatientProfile', on_delete=models.CASCADE, related_name='appointments'
    )
    doctor = models.ForeignKey(
        'accounts.DoctorProfile', on_delete=models.CASCADE, related_name='appointments'
    )
    treatment = models.ForeignKey(
        'treatments.Treatment', on_delete=models.SET_NULL, null=True, related_name='appointments'
    )
    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.CASCADE, related_name='appointments'
    )
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-time']
    
    def __str__(self):
        return f"Appointment: {self.patient} with Dr. {self.doctor} on {self.date}"
    
    def clean(self):
        """Validate no overlapping appointments."""
        if self.date and self.time and self.doctor_id:
            overlapping = Appointment.objects.filter(
                doctor=self.doctor,
                date=self.date,
                time=self.time,
                status__in=[self.Status.PENDING, self.Status.APPROVED]
            ).exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError('This time slot is already booked for this doctor.')
