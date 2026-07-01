from django.contrib import admin
from .models import Treatment, TreatmentImage, MedicalRecord

class TreatmentImageInline(admin.TabularInline):
    model = TreatmentImage
    extra = 0

@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'duration_minutes', 'clinic', 'is_active']
    list_filter = ['category', 'clinic', 'is_active']
    search_fields = ['name', 'description']
    inlines = [TreatmentImageInline]

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'treatment', 'created_at']
    list_filter = ['created_at']
