from django.db import models


class Treatment(models.Model):
    """Aesthetic treatment offered by a clinic."""
    
    class Category(models.TextChoices):
        FACIAL = 'FACIAL', 'Facial Treatment'
        BOTOX = 'BOTOX', 'Botox'
        FILLER = 'FILLER', 'Dermal Filler'
        LASER = 'LASER', 'Laser Treatment'
        CHEMICAL_PEEL = 'CHEMICAL_PEEL', 'Chemical Peel'
        HAIR = 'HAIR', 'Hair Treatment'
        BODY = 'BODY', 'Body Contouring'
        SKIN = 'SKIN', 'Skin Rejuvenation'
        OTHER = 'OTHER', 'Other'
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.PositiveIntegerField(help_text='Duration in minutes')
    sessions_count = models.PositiveIntegerField(default=1, help_text='Recommended number of sessions')
    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.CASCADE, related_name='treatments'
    )
    doctors = models.ManyToManyField(
        'accounts.DoctorProfile', related_name='treatments', blank=False
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} — {self.get_category_display()}"
    
    @property
    def average_rating(self):
        from reviews.models import Review
        avg = Review.objects.filter(treatment=self).aggregate(
            models.Avg('rating')
        )['rating__avg']
        return round(avg, 1) if avg else 0


class TreatmentImage(models.Model):
    """Before/After images for treatments."""
    treatment = models.ForeignKey(Treatment, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='treatments/')
    is_before = models.BooleanField(default=True, help_text='True=Before, False=After')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        label = "Before" if self.is_before else "After"
        return f"{label} — {self.treatment.name}"


class MedicalRecord(models.Model):
    """Patient medical record for a treatment session."""
    class Status(models.TextChoices):
        EN_COURS = 'EN_COURS', 'En cours'
        TERMINE = 'TERMINE', 'Terminé'
        SUIVI = 'SUIVI', 'En suivi'

    patient = models.ForeignKey(
        'accounts.PatientProfile', on_delete=models.CASCADE, related_name='medical_records'
    )
    doctor = models.ForeignKey(
        'accounts.DoctorProfile', on_delete=models.CASCADE, related_name='medical_records'
    )
    treatment = models.ForeignKey(
        Treatment, on_delete=models.SET_NULL, null=True, blank=True, related_name='records'
    )
    diagnosis = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EN_COURS)
    notes = models.TextField()
    prescription = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Record for {self.patient} — {self.created_at:%Y-%m-%d}"


class MedicalRecordImage(models.Model):
    """Images attached to medical records."""
    record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='medical_records/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
