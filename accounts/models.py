from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user with role-based access."""
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        DOCTOR = 'DOCTOR', 'Doctor'
        PATIENT = 'PATIENT', 'Patient'
        CLINIC = 'CLINIC', 'Clinic Manager'
    
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PATIENT)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN
    
    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR
    
    @property
    def is_patient(self):
        return self.role == self.Role.PATIENT

    @property
    def is_clinic_manager(self):
        return self.role == self.Role.CLINIC


class DoctorProfile(models.Model):
    """Extended profile for doctors."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='doctors'
    )
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()} — {self.specialization}"


class PatientProfile(models.Model):
    """Extended profile for patients."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    medical_history = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    blood_type = models.CharField(max_length=5, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"Patient: {self.user.get_full_name()}"


class ClinicManagerProfile(models.Model):
    """Extended profile for clinic managers."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='clinic_manager_profile')
    clinic = models.ForeignKey(
        'clinics.Clinic', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='managers'
    )
    
    def __str__(self):
        clinic_name = self.clinic.name if self.clinic else 'Unassigned'
        return f"Manager: {self.user.get_full_name()} — {clinic_name}"
